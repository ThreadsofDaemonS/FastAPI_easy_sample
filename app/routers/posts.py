from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.cache import cache_key_for_posts_list, invalidate_prefix, redis_cache
from app.deps import CurrentUser, PostServiceDep
from app.pagination import encode_cursor
from app.schemas import CursorPage, PostCreate, PostRead, PostWithAuthor
from app.services import PostService
from app.tasks import send_post_notification
from app.utils import Timer, stream_posts_csv

router = APIRouter(prefix="/posts", tags=["posts"])


@router.post("/", response_model=PostRead, status_code=201)
async def create_post(
    data: PostCreate,
    current_user: CurrentUser,
    service: PostServiceDep,
) -> PostRead:
    post = await service.create_post(title=data.title, body=data.body, author=current_user)
    await invalidate_prefix("posts:list:")  # кеш списку тепер застарілий
    send_post_notification.delay(post.id, current_user.email)  # летить у RabbitMQ, виконає Celery worker
    return PostRead.model_validate(post)


@redis_cache(ttl=30, key_builder=cache_key_for_posts_list)
async def _cached_list_posts(service: PostService, *, limit: int, cursor: str | None) -> dict:
    with Timer("list_posts query"):
        posts = await service.list_posts(limit=limit, cursor=cursor)

    next_cursor = encode_cursor(posts[-1]) if len(posts) == limit else None
    page = CursorPage(
        items=[PostWithAuthor.model_validate(p) for p in posts],
        next_cursor=next_cursor,
    )
    return page.model_dump(mode="json")


@router.get("/", response_model=CursorPage)
async def list_posts(
    service: PostServiceDep,
    limit: int = Query(20, le=100),
    cursor: str | None = None,
) -> dict:
    # перший виклик для цього limit/cursor йде в БД, наступні 30с - з Redis
    return await _cached_list_posts(service, limit=limit, cursor=cursor)


@router.get("/export")
async def export_posts_csv(service: PostServiceDep) -> StreamingResponse:
    posts = await service.list_posts(limit=1000, cursor=None)
    return StreamingResponse(stream_posts_csv(posts), media_type="text/csv")


@router.get("/{post_id}", response_model=PostWithAuthor)
async def get_post(post_id: int, service: PostServiceDep) -> PostWithAuthor:
    post = await service.get_post(post_id)
    return PostWithAuthor.model_validate(post)

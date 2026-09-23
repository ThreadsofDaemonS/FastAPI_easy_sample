from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Post, User
from app.pagination import decode_cursor


class UserRepository:
    """Repository ховає деталі доступу до даних - service layer не знає про SQLAlchemy."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, email: str) -> User | None:
        # аналог filter(...).first(): optional-пошук
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def create(self, *, email: str, hashed_password: str) -> User:
        user = User(email=email, hashed_password=hashed_password)
        self.session.add(user)
        await self.session.flush()  # SQL пішов у БД, commit ще ні
        return user


class PostRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, *, title: str, body: str, author_id: int) -> Post:
        post = Post(title=title, body=body, author_id=author_id)
        self.session.add(post)
        await self.session.flush()
        return post

    async def get_by_id(self, post_id: int) -> Post | None:
        stmt = (
            select(Post)
            .where(Post.id == post_id)
            .options(selectinload(Post.author))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_page(self, *, limit: int, cursor: str | None) -> list[Post]:
        """Keyset/cursor pagination замість OFFSET - стабільна і швидка на великих таблицях."""
        stmt = (
            select(Post)
            .options(selectinload(Post.author))  # eager load, щоб уникнути N+1 на author
            .order_by(Post.created_at.desc(), Post.id.desc())
            .limit(limit)
        )
        if cursor:
            created_at, post_id = decode_cursor(cursor)
            # (created_at, id) < (cursor_created_at, cursor_id), розписано через OR/AND -
            # row-value порівняння підтримується не всіма SQLite-збірками
            stmt = stmt.where(
                or_(
                    Post.created_at < created_at,
                    and_(Post.created_at == created_at, Post.id < post_id),
                )
            )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def increment_views(self, post_id: int) -> None:
        # аналог Django F("views") + 1: атомарний UPDATE на рівні БД, без race condition
        stmt = update(Post).where(Post.id == post_id).values(views=Post.views + 1)
        await self.session.execute(stmt)

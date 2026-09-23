import json
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from redis.asyncio import Redis

from app.config import settings

P = ParamSpec("P")
R = TypeVar("R")

_redis: Redis | None = None


async def get_redis() -> Redis:
    """Лінивий singleton-клієнт. Не тримаємо connection pool у глобальному стані модуля вручну."""
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def redis_cache(
    ttl: int,
    key_builder: Callable[..., str],
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Кешуючий декоратор. Неправильний кеш - швидка брехня, тому TTL обов'язковий.

    functools.wraps зберігає оригінальну сигнатуру функції: FastAPI унаслідує її
    через __wrapped__ і зможе далі резолвити Depends(...) у обгорнутому endpoint.
    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            redis = await get_redis()
            key = key_builder(*args, **kwargs)

            cached = await redis.get(key)
            if cached is not None:
                return json.loads(cached)  # type: ignore[return-value]

            result = await func(*args, **kwargs)
            await redis.set(key, json.dumps(result, default=str), ex=ttl)
            return result

        return wrapper

    return decorator


async def invalidate_prefix(prefix: str) -> None:
    """Викликати після будь-якого запису, що робить кешовані GET-и застарілими."""
    redis = await get_redis()
    async for key in redis.scan_iter(match=f"{prefix}*"):
        await redis.delete(key)


def cache_key_for_posts_list(*args: Any, limit: int = 20, cursor: str | None = None, **kwargs: Any) -> str:
    return f"posts:list:limit={limit}:cursor={cursor}"

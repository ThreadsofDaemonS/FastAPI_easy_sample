from collections.abc import AsyncGenerator
from unittest.mock import Mock

import fakeredis.aioredis
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.cache as cache_module
from app.celery_app import celery_app
from app.database import Base, get_db
from app.deps import get_email_sender
from app.main import app as fastapi_app


@pytest.fixture(autouse=True)
def celery_eager() -> None:
    """Без реального RabbitMQ у тестах: задачі виконуються синхронно і одразу."""
    celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)


@pytest.fixture(autouse=True)
async def fake_redis(monkeypatch: pytest.MonkeyPatch) -> AsyncGenerator[None, None]:
    """Redis - зовнішня межа системи, тому мокаємо її fakeredis, а не піднімаємо реальний сервер."""
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)

    async def _get_redis():
        return client

    monkeypatch.setattr(cache_module, "get_redis", _get_redis)
    yield
    await client.flushall()


@pytest.fixture
async def test_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    session_maker = async_sessionmaker(bind=test_engine, expire_on_commit=False)
    async with session_maker() as session:
        yield session


@pytest.fixture
def mock_email_sender() -> Mock:
    return Mock()


@pytest.fixture
async def client(test_engine, mock_email_sender: Mock) -> AsyncGenerator[AsyncClient, None]:
    session_maker = async_sessionmaker(bind=test_engine, expire_on_commit=False)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_maker() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[get_email_sender] = lambda: mock_email_sender

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    fastapi_app.dependency_overrides.clear()

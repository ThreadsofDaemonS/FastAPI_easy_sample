from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Централізований конфіг. pydantic-settings читає .env і env vars."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/fastapi_easy_sample"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "amqp://guest:guest@localhost:5672//"
    celery_result_backend: str = "redis://localhost:6379/1"

    secret_key: str = "change-me-please-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15

    debug: bool = True


@lru_cache
def get_settings() -> Settings:
    # lru_cache тут виконує роль простого singleton без глобального стану модуля
    return Settings()


settings = get_settings()

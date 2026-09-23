import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

from app.exceptions import register_exception_handlers
from app.routers import posts, users

app = FastAPI(title="FastAPI Easy Sample", version="0.1.0")

register_exception_handlers(app)

app.include_router(users.router)
app.include_router(posts.router)


@app.middleware("http")
async def add_timing_header(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Мінімальний observability-приклад: timing кожного запиту в лог і в заголовок."""
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"
    print(f"{request.method} {request.url.path} -> {response.status_code} in {duration_ms:.2f}ms")
    return response


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}

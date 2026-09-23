import time
from collections.abc import Generator, Iterable
from types import TracebackType

from app.models import Post


class Timer:
    """Context manager: cleanup/лог гарантовано виконається навіть при exception."""

    def __init__(self, label: str):
        self.label = label
        self.elapsed: float = 0.0

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        self.elapsed = time.perf_counter() - self._start
        print(f"[timer] {self.label} took {self.elapsed:.4f}s")
        return False  # не ковтати exception


def stream_posts_csv(posts: Iterable[Post]) -> Generator[str, None, None]:
    """Lazy generator: не тримає весь CSV у пам'яті одразу, підходить для великих вивантажень."""
    yield "id,title,author_id,views,created_at\n"
    for post in posts:
        title = post.title.replace(",", " ")
        yield f"{post.id},{title},{post.author_id},{post.views},{post.created_at.isoformat()}\n"

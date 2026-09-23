from datetime import datetime, timezone

from app.models import Post
from app.utils import Timer, stream_posts_csv


def test_timer_measures_elapsed_time() -> None:
    with Timer("unit-test") as timer:
        pass

    assert timer.elapsed >= 0


def test_timer_does_not_swallow_exceptions() -> None:
    try:
        with Timer("unit-test"):
            raise ValueError("boom")
    except ValueError:
        pass
    else:
        raise AssertionError("Timer swallowed the exception")


def test_stream_posts_csv_is_lazy_generator() -> None:
    posts = [
        Post(id=1, title="Hello, world", author_id=1, views=0, created_at=datetime.now(timezone.utc)),
        Post(id=2, title="Second", author_id=1, views=5, created_at=datetime.now(timezone.utc)),
    ]

    generator = stream_posts_csv(posts)
    rows = list(generator)

    assert rows[0] == "id,title,author_id,views,created_at\n"
    assert "Hello  world" in rows[1]  # коми в title заміняються на пробіли
    assert len(rows) == 3

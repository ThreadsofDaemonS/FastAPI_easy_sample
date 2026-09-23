import base64
from datetime import datetime

from app.models import Post


def encode_cursor(post: Post) -> str:
    raw = f"{post.created_at.isoformat()}|{post.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, int]:
    raw = base64.urlsafe_b64decode(cursor.encode()).decode()
    created_at_raw, post_id_raw = raw.split("|")
    return datetime.fromisoformat(created_at_raw), int(post_id_raw)

from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# --- Users ---------------------------------------------------------------

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    is_active: bool
    created_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@dataclass(frozen=True)
class TokenPair:
    """DTO для пари токенів. frozen=True - ближче до immutable value object."""

    access_token: str
    token_type: str = "bearer"


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Posts -----------------------------------------------------------------

class PostCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    body: str


class PostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    body: str
    author_id: int
    views: int
    created_at: datetime


class PostWithAuthor(PostRead):
    author: UserRead


class CursorPage(BaseModel):
    """Відповідь для keyset/cursor pagination - без OFFSET на великих таблицях."""

    items: list[PostWithAuthor]
    next_cursor: str | None = None

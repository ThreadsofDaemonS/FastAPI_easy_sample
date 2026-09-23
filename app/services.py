from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import InvalidCredentialsError, PostNotFoundError, UserAlreadyExistsError
from app.models import Post, User
from app.repositories import PostRepository, UserRepository
from app.security import create_access_token, hash_password, verify_password


class EmailSender(Protocol):
    """D з SOLID: UserService залежить від абстракції, а не від конкретного email-провайдера."""

    def send(self, to: str, subject: str, body: str) -> None: ...


class ConsoleEmailSender:
    """Проста реалізація для dev/демо. У production тут був би SMTP/SES/SendGrid клієнт."""

    def send(self, to: str, subject: str, body: str) -> None:
        print(f"[email] to={to} subject={subject!r} body={body!r}")


class UserService:
    def __init__(self, session: AsyncSession, email_sender: EmailSender):
        self.session = session
        self.repo = UserRepository(session)
        self.email_sender = email_sender

    async def register(self, *, email: str, password: str) -> User:
        existing = await self.repo.get_by_email(email)
        if existing is not None:
            raise UserAlreadyExistsError(f"User with email {email} already exists")

        user = await self.repo.create(email=email, hashed_password=hash_password(password))
        await self.session.commit()

        self.email_sender.send(email, "Welcome", "Дякуємо за реєстрацію!")
        return user

    async def authenticate(self, *, email: str, password: str) -> str:
        user = await self.repo.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError("Invalid email or password")

        return create_access_token(subject=str(user.id))


class PostService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = PostRepository(session)

    async def create_post(self, *, title: str, body: str, author: User) -> Post:
        post = await self.repo.create(title=title, body=body, author_id=author.id)
        await self.session.commit()
        # без цього post.author лишиться "порожнім" в об'єкті, доки не звернутись до БД знову
        post.author = author
        return post

    async def get_post(self, post_id: int) -> Post:
        post = await self.repo.get_by_id(post_id)
        if post is None:
            raise PostNotFoundError(f"Post {post_id} not found")

        await self.repo.increment_views(post_id)
        await self.session.commit()
        # refresh тільки views: якщо рефрешити весь об'єкт, SQLAlchemy скине loader
        # relationship "author" і подальший доступ до post.author впаде в async lazy-load (MissingGreenlet)
        await self.session.refresh(post, attribute_names=["views"])
        return post

    async def list_posts(self, *, limit: int, cursor: str | None) -> list[Post]:
        return await self.repo.list_page(limit=limit, cursor=cursor)

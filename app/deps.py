from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import InvalidCredentialsError
from app.models import User
from app.repositories import UserRepository
from app.security import InvalidTokenError, decode_access_token
from app.services import ConsoleEmailSender, EmailSender, PostService, UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DbSession,
) -> User:
    try:
        user_id = decode_access_token(token)
    except InvalidTokenError as exc:
        raise InvalidCredentialsError("Could not validate credentials") from exc

    user = await UserRepository(db).get_by_id(int(user_id))
    if user is None:
        raise InvalidCredentialsError("User not found")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_email_sender() -> EmailSender:
    return ConsoleEmailSender()


def get_user_service(
    db: DbSession,
    email_sender: Annotated[EmailSender, Depends(get_email_sender)],
) -> UserService:
    return UserService(db, email_sender)


def get_post_service(db: DbSession) -> PostService:
    return PostService(db)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
PostServiceDep = Annotated[PostService, Depends(get_post_service)]

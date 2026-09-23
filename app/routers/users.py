from fastapi import APIRouter
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from fastapi import Depends

from app.deps import CurrentUser, UserServiceDep
from app.schemas import Token, UserCreate, UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=UserRead, status_code=201)
async def register(data: UserCreate, service: UserServiceDep) -> UserRead:
    user = await service.register(email=data.email, password=data.password)
    return UserRead.model_validate(user)


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: UserServiceDep,
) -> Token:
    # OAuth2PasswordRequestForm приходить як username/password, ми трактуємо username як email
    access_token = await service.authenticate(email=form_data.username, password=form_data.password)
    return Token(access_token=access_token)


@router.get("/me", response_model=UserRead)
async def me(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)

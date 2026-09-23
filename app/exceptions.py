from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    """Базова доменна помилка - НЕ HTTPException, щоб не змішувати шари."""

    status_code = 400

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class UserAlreadyExistsError(DomainError):
    status_code = 409


class InvalidCredentialsError(DomainError):
    status_code = 401


class PostNotFoundError(DomainError):
    status_code = 404


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        # тут гарне місце для логування неочікуваних помилок; очікувані - просто мапляться в response
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

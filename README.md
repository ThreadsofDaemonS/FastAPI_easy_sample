# FastAPI Easy Sample

Легкий навчальний проект, який демонструє на реальному коді більшість тем із
`middle_python_django_interview_cheatsheet` (окрім суто-Django частини) плюс
Celery + RabbitMQ + Redis.

Це блог-подібний API: реєстрація/логін через JWT, пости з cursor pagination,
кешування списку постів у Redis, фонова задача-нотифікація через Celery/RabbitMQ.

## Стек

FastAPI · SQLAlchemy 2.0 (async) · PostgreSQL · Alembic · Redis · Celery · RabbitMQ · pytest

## Швидкий старт (Docker)

```bash
cp .env.example .env
docker compose up -d --build

# перша міграція (генерується автогенерейтом, бо БД вже піднята)
docker compose exec api alembic revision --autogenerate -m "init"
docker compose exec api alembic upgrade head
```

API: http://localhost:8000/docs
RabbitMQ management UI: http://localhost:15672 (guest/guest)

## Локально без Docker (для розробки/тестів)

```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt

pytest                       # тести не потребують реальних Postgres/Redis/RabbitMQ
```

Тести піднімають SQLite in-memory замість Postgres, fakeredis замість Redis,
а Celery працює в `task_always_eager` режимі (без RabbitMQ) - зовнішні межі
системи мокаються, а не сама бізнес-логіка (`tests/conftest.py`).

## Що де подивитись (мапа на шпаргалку)

| Тема зі шпаргалки | Де в коді |
|---|---|
| Mutable default arguments, generators, decorators | `app/utils.py` (generator `stream_posts_csv`), `app/cache.py` (`redis_cache` + `functools.wraps`) |
| Context manager (`__enter__`/`__exit__`) | `app/utils.py::Timer` |
| dataclass (frozen, value object) | `app/schemas.py::TokenPair` |
| classmethod/staticmethod, SOLID (Protocol, DI) | `app/services.py` (`EmailSender` Protocol, `UserService`) |
| Exceptions, `raise ... from`, чистий error handling | `app/exceptions.py`, `app/security.py::decode_access_token` |
| async/await, чому `time.sleep` в async - зло | `app/tasks.py` (коментар про різницю Celery worker vs event loop) |
| FastAPI `Depends`, вкладені залежності | `app/deps.py` |
| Pydantic: розділення input/output схем | `app/schemas.py` (`UserCreate` vs `UserRead`, password_hash ніколи не йде в response) |
| QuerySet-подібна lazy-евалюація, `select_related`/`prefetch_related` аналог | `app/repositories.py::PostRepository` (`selectinload(Post.author)`) |
| N+1 problem | коментарі в `repositories.py`, `PostWithAuthor` eager-loaded |
| F() expressions (атомарний UPDATE) | `app/repositories.py::increment_views` |
| `transaction.atomic` / commit-rollback | `app/services.py` (commit після кожної use-case операції) |
| Offset vs cursor pagination | `app/pagination.py`, `app/repositories.py::list_page` |
| Async SQLAlchemy lazy-loading pitfall (`MissingGreenlet`) | коментар у `app/services.py::PostService.get_post` |
| Alembic autogenerate vs ручні міграції | `alembic/env.py`, `alembic.ini` |
| pytest fixtures, mock зовнішніх сервісів | `tests/conftest.py`, `tests/test_users.py` (мок `EmailSender`) |
| Hashing паролів (bcrypt), JWT, ризики JWT | `app/security.py` |
| SQL injection захист через ORM/параметризацію | весь `repositories.py` - нема raw SQL зі склеюванням рядків |
| Docker image/container/volume, docker-compose | `Dockerfile`, `docker-compose.yml` |
| Redis як cache + інвалідація | `app/cache.py`, виклик `invalidate_prefix` у `routers/posts.py::create_post` |
| Celery + RabbitMQ (broker) + Redis (result backend) | `app/celery_app.py`, `app/tasks.py` |
| GIL і CPU-bound vs I/O-bound | коментар у `app/tasks.py::compute_heavy_report` |
| Performance/observability (timing) | `app/main.py` middleware `add_timing_header` |
| Service layer / Repository pattern | `app/services.py` + `app/repositories.py` |

## Структура

```
app/
  main.py            FastAPI app, middleware, exception handlers
  config.py          pydantic-settings конфіг
  database.py        async engine/session, Base, get_db
  models.py           SQLAlchemy моделі (User, Post) + індекси
  schemas.py          Pydantic input/output схеми
  security.py          password hashing (bcrypt), JWT
  deps.py               Depends: get_db, get_current_user, service factories
  exceptions.py          доменні винятки + exception handlers
  repositories.py         доступ до даних (SQLAlchemy select/update)
  services.py               бізнес-логіка (UserService, PostService, EmailSender Protocol)
  cache.py                   Redis cache decorator + інвалідація
  pagination.py                cursor/keyset pagination helpers
  utils.py                      generator (CSV export), Timer context manager
  celery_app.py                  Celery app (RabbitMQ broker, Redis backend)
  tasks.py                        Celery задачі
  routers/
    users.py                        /users/register, /login, /me
    posts.py                        /posts CRUD, cursor pagination, export, notify
alembic/               міграції (async env.py)
tests/                  pytest + httpx AsyncClient, fakeredis, celery eager mode
```

## Ключові ендпоінти

- `POST /users/register` - реєстрація, шле welcome-email через `EmailSender`
- `POST /users/login` - OAuth2 password flow, повертає JWT access token
- `GET /users/me` - поточний користувач (потребує `Authorization: Bearer <token>`)
- `POST /posts/` - створити пост (auth), інвалідує кеш списку, ставить Celery-задачу нотифікації
- `GET /posts/?limit=&cursor=` - cursor pagination, кешується в Redis на 30с
- `GET /posts/{id}` - деталі поста, атомарно інкрементує `views`
- `GET /posts/export` - CSV-стрім (generator, без буферизації всього результату в пам'яті)

## Відомі спрощення (свідомо, бо проект навчальний)

- Немає refresh-токенів і revocation списку - тільки короткоживучий access token.
- Немає rate limiting - хоча Redis для цього прекрасно підходить (`INCR` + `EXPIRE`).
- Автогенерована Alembic-міграція не закомічена в репозиторій - генерується локально,
  бо схема без запущеної БД для autogenerate не потрібна, а закомічена міграція
  застаріє разом з моделями.

import time

from app.celery_app import celery_app
from app.services import ConsoleEmailSender


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def send_post_notification(self, post_id: int, author_email: str) -> dict:
    """I/O-bound задача виконується в окремому worker-процесі, не в event loop FastAPI.

    Тут time.sleep() - це НЕ та сама помилка, що з async def + time.sleep() у FastAPI:
    Celery worker synchronous і не ділить event loop з API-процесом.
    """
    try:
        time.sleep(1)  # імітація виклику email-провайдера
        ConsoleEmailSender().send(
            author_email,
            "Your post is live",
            f"Post {post_id} was published successfully.",
        )
        return {"post_id": post_id, "status": "sent"}
    except Exception as exc:  # зовнішній сервіс може впасти - тут retry доречний, не голий except: pass
        raise self.retry(exc=exc) from exc


@celery_app.task
def compute_heavy_report(n: int) -> int:
    """CPU-bound приклад. GIL не дає паралелізму всередині одного процесу,
    тому масштабування CPU-bound задач у Celery робиться через кілька worker-процесів
    (--pool=prefork), а не через threads.
    """
    return sum(i * i for i in range(n))

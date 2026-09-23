from celery import Celery

from app.config import settings

celery_app = Celery(
    "fastapi_easy_sample",
    broker=settings.celery_broker_url,       # RabbitMQ - черга задач
    backend=settings.celery_result_backend,  # Redis - зберігання результатів
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # окрема, коротка queue-специфічна retry-політика, а не голий except: pass у таски
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

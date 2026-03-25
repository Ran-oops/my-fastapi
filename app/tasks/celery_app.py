from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "enterprise_fastapi",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_max_retries=3,
    task_default_retry_delay=60,
    task_time_limit=300,
    task_soft_time_limit=240,
)

# Import signals to register them
import app.tasks.signals  # noqa: F401, E402

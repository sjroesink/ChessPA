from celery import Celery
from app.config import settings

celery_app = Celery(
    "chesspa",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    beat_schedule={
        "sync-games-every-30-min": {
            "task": "app.worker.tasks.sync_all_accounts",
            "schedule": 1800.0,
        },
    },
)

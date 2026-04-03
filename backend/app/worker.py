from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "perception",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "process-schedules": {
            "task": "app.tasks.process_schedules",
            "schedule": 60.0,  # every 60 seconds
        },
    },
)

# Auto-discover tasks in app.tasks
celery_app.autodiscover_tasks(["app"])

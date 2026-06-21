from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "hr_scoring",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks"],
)

celery_app.conf.timezone = "UTC"
celery_app.conf.beat_schedule = {
    "check-scheduled-searches": {
        "task": "app.tasks.check_and_dispatch",
        "schedule": crontab(minute="*"),  # каждую минуту
    },
}

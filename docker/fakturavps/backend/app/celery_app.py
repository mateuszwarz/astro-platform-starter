from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "fakturavps",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.scheduled", "app.tasks.email_tasks"]
)

celery_app.conf.timezone = "Europe/Warsaw"
celery_app.conf.beat_schedule = {
    "mark-overdue-invoices": {
        "task": "app.tasks.scheduled.mark_overdue_invoices",
        "schedule": crontab(hour=0, minute=1),
    },
    "fetch-email-invoices": {
        "task": "app.tasks.email_tasks.fetch_all_email_sources",
        "schedule": crontab(minute="*/5"),  # every 5 minutes
    },
}

celery_app.conf.update(
    result_expires=3600,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
)

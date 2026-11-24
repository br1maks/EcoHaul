
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "ecohaul",
    broker=settings.REDIS_URL.replace("/0", "/1"),
    backend=settings.REDIS_URL.replace("/0", "/2")
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    timezone="Europe/Minsk",
    enable_utc=True,

    include=[
        "app.tasks.orders",
        "app.tasks.subscriptions",
    ],

    beat_schedule={
        "auto-cancel-expired-orders": {
            "task": "app.tasks.orders.auto_cancel_expired_orders",
            "schedule": 300.0,
        },

        "check-expired-subscriptions": {
            "task": "app.tasks.subscriptions.check_expired_subscriptions",
            "schedule": 3600.0,
        }
    },
)

"""Persist the inbox entry and its realtime hint in the order's transaction."""
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import NotificationChannel, NotificationType
from app.models.notification import Notification
from app.services.outbox import queue_websocket


def queue_order_update(db: AsyncSession, user_id: UUID, message: dict) -> None:
    data = message["data"]
    status = data["new_status"]
    notification_id = uuid4()
    titles = {
        "IN_PROGRESS": "Курьер в пути",
        "ARRIVED": "Курьер прибыл",
        "COMPLETED": "Заказ выполнен",
        "CANCELLED": "Заказ отменён",
    }
    types = {
        "COMPLETED": NotificationType.ORDER_COMPLETED,
        "CANCELLED": NotificationType.ORDER_CANCELLED,
    }
    db.add(
        Notification(
            id=notification_id,
            user_id=user_id,
            order_id=UUID(data["order_id"]),
            notification_type=types.get(status, NotificationType.ORDER_STARTED),
            channel=NotificationChannel.IN_APP,
            title=titles.get(status, "Статус заказа"),
            message=data["message"],
            sent_at=datetime.now(timezone.utc),
        )
    )
    message = {**message, "data": {**data, "notification_id": str(notification_id)}}
    queue_websocket(db, user_id, message, aggregate_key=f"order:{data['order_id']}")

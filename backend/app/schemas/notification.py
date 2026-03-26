
from typing import Optional, Any
from uuid import UUID
from datetime import datetime

from pydantic import Field, field_validator, model_validator

from app.models.enums import NotificationType, NotificationChannel
from app.schemas.common import BaseSchema, UUIDMixin, TimestampMixin

class NotificationBase(BaseSchema):
    user_id: UUID
    order_id: Optional[UUID] = None
    notification_type: NotificationType
    channel: NotificationChannel
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1)
    data: Optional[str] = None
    is_read: bool = False
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    retry_count: int = Field(default=0, ge=0, le=10)
    last_error: Optional[str] = None
    telegram_message_id: Optional[str] = Field(None, max_length=100)

    @model_validator(mode="after")
    def validate_notification_logic(self):
        if self.is_read and not self.read_at:
            raise ValueError("read_at обязателен если is_read = True")

        if self.read_at and self.sent_at and self.read_at < self.sent_at:
            raise ValueError("read_at не может быть раньше sent_at")

        if self.channel == NotificationChannel.TELEGRAM and self.sent_at and not self.telegram_message_id:
            raise ValueError("telegram_message_id обязателен для отправленных TELEGRAM уведомлений")

        if self.last_error and self.retry_count == 0:
            raise ValueError("retry_count должен быть > 0 если есть last_error")

        return self

class NotificationCreate(BaseSchema):
    user_id: UUID
    order_id: Optional[UUID] = None
    notification_type: NotificationType
    channel: NotificationChannel
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1)
    data: Optional[str] = None

class NotificationUpdate(BaseSchema):
    is_read: Optional[bool] = None
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    retry_count: Optional[int] = Field(None, ge=0, le=10)
    last_error: Optional[str] = None
    telegram_message_id: Optional[str] = Field(None, max_length=100)

class NotificationResponse(UUIDMixin, TimestampMixin, NotificationBase):
    is_sent: bool
    is_pending: bool
    is_failed: bool
    is_in_app: bool
    is_telegram: bool
    reading_time_seconds: Optional[int]

    @model_validator(mode="before")
    @classmethod
    def calculate_computed_fields(cls, data: Any) -> Any:
        if hasattr(data, "__dict__"):
            model_data = {
                "id": data.id,
                "created_at": data.created_at,
                "updated_at": data.updated_at,
                "user_id": data.user_id,
                "order_id": data.order_id,
                "notification_type": data.notification_type,
                "channel": data.channel,
                "title": data.title,
                "message": data.message,
                "data": data.data,
                "is_read": data.is_read,
                "sent_at": data.sent_at,
                "read_at": data.read_at,
                "retry_count": data.retry_count,
                "last_error": data.last_error,
                "telegram_message_id": data.telegram_message_id,
                "is_sent": getattr(data, "is_sent", False),
                "is_pending": getattr(data, "is_pending", False),
                "is_failed": getattr(data, "is_failed", False),
                "is_in_app": getattr(data, "is_in_app", False),
                "is_telegram": getattr(data, "is_telegram", False),
                "reading_time_seconds": getattr(data, "reading_time_seconds", None),
            }
            data = model_data
        elif isinstance(data, dict):
            sent_at = data.get("sent_at")
            read_at = data.get("read_at")
            retry_count = data.get("retry_count", 0)
            channel = data.get("channel")

            if "is_sent" not in data:
                data["is_sent"] = sent_at is not None

            if "is_pending" not in data:
                data["is_pending"] = sent_at is None and retry_count < 3

            if "is_failed" not in data:
                data["is_failed"] = sent_at is None and retry_count >= 3

            if "is_in_app" not in data:
                data["is_in_app"] = channel == NotificationChannel.IN_APP

            if "is_telegram" not in data:
                data["is_telegram"] = channel == NotificationChannel.TELEGRAM

            if "reading_time_seconds" not in data:
                if sent_at and read_at:
                    delta = read_at - sent_at
                    data["reading_time_seconds"] = int(delta.total_seconds())
                else:
                    data["reading_time_seconds"] = None

        return data

class NotificationBrief(UUIDMixin, BaseSchema):
    notification_type: NotificationType
    channel: NotificationChannel
    title: str
    is_read: bool
    is_sent: bool
    created_at: datetime

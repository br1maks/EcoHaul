from typing import Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy import String, ForeignKey, DateTime, Index, Text, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, IDMixin, TimestampMixin
from .enums import NotificationType, NotificationChannel

class Notification(Base, IDMixin, TimestampMixin):
    __tablename__ = "notifications"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    order_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
    )

    notification_type: Mapped[NotificationType] = mapped_column(
        String(30),
        nullable=False,
    )

    channel: Mapped[NotificationChannel] = mapped_column(
        String(20),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    data: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    last_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    telegram_message_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    user = relationship(
        "User",
        back_populates="notifications",
    )

    order = relationship(
        "Order",
        back_populates="notifications",
    )

    __table_args__ = (
        Index("idx_notification_user_id", "user_id"),
        Index("idx_notification_order_id", "order_id"),
        Index("idx_notification_type", "notification_type"),
        Index("idx_notification_channel", "channel"),
        Index("idx_notification_is_read", "is_read"),
        Index("idx_notification_sent_at", "sent_at"),
        Index("idx_notification_user_read", "user_id", "is_read"),
        Index("idx_notification_user_created", "user_id", "created_at"),
    )

    @property
    def is_sent(self) -> bool:
        return self.sent_at is not None

    @property
    def is_pending(self) -> bool:
        return self.sent_at is None and self.retry_count < 3
    
    @property
    def is_failed(self) -> bool:
        return self.sent_at is None and self.retry_count >= 3 
    
    @property
    def is_in_app(self) -> bool:
        return self.channel == NotificationChannel.IN_APP
    
    @property
    def is_telegram(self) -> bool:
        return self.channel == NotificationChannel.TELEGRAM
    
    @property
    def reading_time_seconds(self) -> Optional[int]:
        if self.sent_at and self.read_at:
            delta = self.read_at - self.sent_at
            return int(delta.total_seconds())
        return None
    
    def __repr__(self) -> str:
        return (
            f"<Notification(id={self.id}, user_id={self.user_id}, "
            f"type={self.notification_type}, channel={self.channel}, "
            f"is_read={self.is_read})>"
        )
    
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta, timezone

from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, IDMixin, TimestampMixin
from .enums import OrderQueueStatus, DeclineReason

class OrderQueue(Base, IDMixin, TimestampMixin):

    __tablename__ = "order_queue"

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )

    courier_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    status: Mapped[OrderQueueStatus] = mapped_column(
        String(20),
        nullable=False,
        default=OrderQueueStatus.OFFERED,
    )

    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    distance_km: Mapped[float] = mapped_column(
        Float,
        nullable=False,

    )

    offered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    responded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    decline_reason: Mapped[Optional[DeclineReason]] = mapped_column(
        String(30),
        nullable=True,

    )

    order = relationship(
        "Order",
        back_populates="queue_offers",
        doc="Заказ который предлагается"
    )

    courier = relationship(
        "User",
        doc="Курьер которому предложен заказ"
    )

    __table_args__ = (
        UniqueConstraint("order_id", "courier_id", name="uq_order_courier"),

        Index("idx_order_queue_order_id", "order_id"),

        Index("idx_order_queue_courier_id", "courier_id"),
        Index("idx_order_queue_status", "status"),
        Index("idx_order_queue_expires_at", "expires_at"),
        Index("idx_order_queue_courier_status", "courier_id", "status"),

        Index("idx_order_queue_order_priority", "order_id", "priority"),
    )

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_active(self) -> bool:
        return self.status == OrderQueueStatus.OFFERED and not self.is_expired

    @property
    def is_accepted(self) -> bool:

        return self.status == OrderQueueStatus.ACCEPTED

    @property
    def is_declined(self) -> bool:
        return self.status == OrderQueueStatus.DECLINED

    @property
    def response_time_seconds(self) -> Optional[int]:
        if self.responded_at and self.offered_at:
            delta = self.responded_at - self.offered_at
            return int(delta.total_seconds())
        return None

    @property
    def time_remaining_seconds(self) -> int:

        now = datetime.now(timezone.utc)
        if now >= self.expires_at:
            return 0
        delta = self.expires_at - now
        return int(delta.total_seconds())

    def __repr__(self) -> str:
        return (
            f"<OrderQueue(id={self.id}, order_id={self.order_id}, "
            f"courier_id={self.courier_id}, status={self.status}, "
            f"priority={self.priority}, distance={self.distance_km}km)>"
        )

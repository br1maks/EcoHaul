from typing import Optional
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Numeric, ForeignKey, DateTime, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, IDMixin, TimestampMixin

class CourierShift(Base, IDMixin, TimestampMixin):
    __tablename__ = "courier_shifts"

    courier_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    orders_completed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    start_location_lat: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 8),
        nullable=True,
    )

    start_location_lon: Mapped[Optional[float]] = mapped_column(
        Numeric(11, 8),
        nullable=True,
    )

    end_location_lat: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 8),
        nullable=True,
    )

    end_location_lon: Mapped[Optional[float]] = mapped_column(
        Numeric(11, 8),
        nullable=True,
    )

    total_distance_km: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=0.0,
    )

    break_duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    early_end_reason: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="Причина досрочного завершения смены (если < 2 часов)"
    )

    courier = relationship(
        "User",
        back_populates="courier_shifts",
        doc="Курьер, работающий в эту смену"
    )

    __table_args__ = (
        Index("idx_courier_shift_courier_id", "courier_id"),
        
        Index("idx_courier_shift_started_at", "started_at"),
        
        Index("idx_courier_shift_ended_at", "ended_at"),
        
        Index("idx_courier_shift_courier_started", "courier_id", "started_at"),
        
        Index("idx_courier_shift_courier_active", "courier_id", "ended_at"),
    )

    @property
    def is_active(self) -> bool:
        return self.ended_at is None

    @property
    def duration_hours(self) -> Optional[float]:
        if not self.ended_at:
            now = datetime.now(timezone.utc)
            delta = now - self.started_at
            return delta.total_seconds() / 3600
        
        delta = self.ended_at - self.started_at
        return delta.total_seconds() / 3600

    @property
    def net_duration_hours(self) -> Optional[float]:
        if not self.duration_hours:
            return None
        return self.duration_hours - (self.break_duration_minutes / 60)

    @property
    def average_distance_per_order(self) -> Optional[float]:
        if self.orders_completed == 0:
            return None
        return float(self.total_distance_km) / self.orders_completed

    @property
    def has_location_data(self) -> bool:
        return (
            self.start_location_lat is not None 
            and self.start_location_lon is not None
        )

    def __repr__(self) -> str:
        status = "ACTIVE" if self.is_active else "ENDED"
        return (
            f"<CourierShift(id={self.id}, courier_id={self.courier_id}, "
            f"status={status}, orders_completed={self.orders_completed})>"
        )
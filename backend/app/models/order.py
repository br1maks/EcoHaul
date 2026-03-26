
from typing import Optional
from uuid import UUID
from datetime import datetime 

from sqlalchemy import String, Integer, Text, Numeric, ForeignKey, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, IDMixin, TimestampMixin, SoftDeleteMixin
from .enums import OrderStatus, GarbageType, SubscriptionTier

class Order(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "orders"

    client_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    courier_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    pickup_address_id: Mapped[UUID] = mapped_column(
        ForeignKey("addresses.id", ondelete="RESTRICT"),
        nullable=False,
    )

    garbage_type: Mapped[GarbageType] = mapped_column(
        String(20),
        nullable=False,
        default=GarbageType.HOUSEHOLD,
    )

    number_of_bags: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[OrderStatus] = mapped_column(
        String(20),
        nullable=False,
        default=OrderStatus.PENDING,
    )

    price_before_discount: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    discount_amount: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=0.0,
    )
    
    final_price: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    subscription_tier_used: Mapped[Optional[SubscriptionTier]] = mapped_column(
        String(20),
        nullable=True,
    )

    distance_km: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        doc="Фактическое расстояние которое проехал курьер (км). Заполняется при завершении"
    )

    scheduled_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Запланированное время когда курьер должен приехать"
    )

    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Приоритет заказа (выше = важнее). Автоматически повышается со временем ожидания"
    )

    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Время истечения заказа для курьеров (показывает срочность). Если None - заказ не истекает"
    )

    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Когда курьер принял заказ (статус → ASSIGNED)"
    )

    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Когда курьер начал движение (статус → IN_PROGRESS)"
    )

    arrived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Когда курьер прибыл на место (статус → ARRIVED)"
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    cancellation_reason: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="Причина отмены заказа"
    )

    cancelled_by_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="Кто отменил заказ (client_id или courier_id или admin_id)"
    )

    client = relationship(
        "User",
        foreign_keys=[client_id],
        back_populates="orders_as_client",
    )
    
    courier = relationship(
        "User",
        foreign_keys=[courier_id],
        back_populates="orders_as_courier",
    )

    cancelled_by = relationship(
        "User",
        foreign_keys=[cancelled_by_id],
        doc="Пользователь который отменил заказ"
    )

    pickup_address = relationship(
        "Address",
        back_populates="orders",
    )
    
    payment = relationship(
        "Payment",
        back_populates="order",
        uselist=False,
    )
    
    reviews = relationship(
        "Review",
        back_populates="order",
    )
    
    queue_offers = relationship(
        "OrderQueue",
        back_populates="order",
        doc="История предложений этого заказа курьерам"
    )

    notifications = relationship(
        "Notification",
        back_populates="order",
        doc="Уведомления связанные с этим заказом"
    )

    __table_args__ = (
        Index("idx_order_client_id", "client_id"),
        Index("idx_order_courier_id", "courier_id"),
        Index("idx_order_pickup_address_id", "pickup_address_id"),
        Index("idx_order_status", "status"),
        Index("idx_order_scheduled_time", "scheduled_time"),
        Index("idx_order_completed_at", "completed_at"),
        Index("idx_order_cancelled_by_id", "cancelled_by_id"),
        Index("idx_order_courier_status", "courier_id", "status"),
        Index("idx_order_client_created", "client_id", "created_at"),
        Index("idx_order_priority", "priority"),
        Index("idx_order_expires_at", "expires_at"),
        Index("idx_order_status_priority", "status", "priority"),
    )

    @property
    def is_pending(self) -> bool:
        return self.status == OrderStatus.PENDING
    
    @property
    def is_active(self) -> bool:
        return self.status in [OrderStatus.PENDING, OrderStatus.ASSIGNED, OrderStatus.IN_PROGRESS]
    
    @property
    def is_completed(self) -> bool:
        return self.status == OrderStatus.COMPLETED
    
    @property
    def has_discount(self) -> bool:
        return self.discount_amount > 0
    
    @property
    def discount_percentage(self) -> float:
        if self.price_before_discount == 0:
            return 0.0
        return round((self.discount_amount / self.price_before_discount) * 100, 2)
    
    @property
    def duration_minutes(self) -> Optional[int]:
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return int(delta.total_seconds() / 60)
        return None

    @property
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        from datetime import timezone
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def time_remaining_seconds(self) -> Optional[int]:
        if not self.expires_at:
            return None
        from datetime import timezone
        now = datetime.now(timezone.utc)
        if now >= self.expires_at:
            return 0
        delta = self.expires_at - now
        return int(delta.total_seconds())

    def __repr__(self) -> str:
        return (
            f"<Order(id={self.id}, client_id={self.client_id}, "
            f"status={self.status}, final_price={self.final_price} BYN)>"
        )


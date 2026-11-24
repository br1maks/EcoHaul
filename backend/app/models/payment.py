from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, Numeric, ForeignKey, DateTime, Index, Text, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, IDMixin, TimestampMixin
from .enums import PaymentType, PaymentMethod, PaymentStatus

class Payment(Base, IDMixin, TimestampMixin):

    __tablename__ = "payments"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    order_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
    )

    subscription_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
    )

    refund_for_payment_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
    )

    payment_type: Mapped[PaymentType] = mapped_column(
        String(30),
        nullable=False,
    )

    payment_method: Mapped[PaymentMethod] = mapped_column(
        String(20),
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    status: Mapped[PaymentStatus] = mapped_column(
        String(20),
        nullable=False,
        default=PaymentStatus.PENDING,
    )

    yookassa_payment_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
    )

    yookassa_response: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    failed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BYN", server_default="BYN")
    idempotency_key: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True))
    request_hash: Mapped[Optional[str]] = mapped_column(String(64))
    checkout_payload: Mapped[Optional[dict]] = mapped_column(JSONB)
    creation_state: Mapped[str] = mapped_column(String(20), default="LEGACY", server_default="LEGACY")
    provider_key: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True))
    provider_key_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    creation_lease: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True))
    lease_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    confirmation_url: Mapped[Optional[str]] = mapped_column(Text)
    checkout_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    next_reconcile_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    reconcile_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    settlement_applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    user = relationship(
        "User",
        back_populates="payments",
        doc="Пользователь который совершает платёж"
    )

    order = relationship(
        "Order",
        back_populates="payments",
        doc="Заказ за который производится оплата"
    )

    subscription = relationship(
        "Subscription",
        back_populates="payments",
        foreign_keys=[subscription_id],
        doc="Подписка за которую производится оплата"
    )

    original_payment = relationship(
        "Payment",
        remote_side="[Payment.id]",
        foreign_keys=[refund_for_payment_id],
        backref="refunds",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_payment_user_idempotency"),
        UniqueConstraint("provider_key", name="uq_payment_provider_key"),
        Index("ix_payment_reconcile", "status", "next_reconcile_at"),
        Index("idx_payment_user_id", "user_id"),

        Index("idx_payment_order_id", "order_id"),

        Index("idx_payment_subscription_id", "subscription_id"),

        Index("idx_payment_refund_for", "refund_for_payment_id"),

        Index("idx_payment_type", "payment_type"),

        Index("idx_payment_status", "status"),

        Index("idx_payment_user_type", "user_id", "payment_type"),

        Index("idx_payment_user_status", "user_id", "status"),

        Index("idx_payment_yookassa_id", "yookassa_payment_id"),
    )

    @property
    def is_pending(self) -> bool:
        return self.status == PaymentStatus.PENDING

    @property
    def is_completed(self) -> bool:
        return self.status == PaymentStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        return self.status == PaymentStatus.FAILED

    @property
    def is_cancelled(self) -> bool:
        return self.status == PaymentStatus.CANCELLED

    @property
    def is_finalized(self) -> bool:
        return self.status in [
            PaymentStatus.COMPLETED,
            PaymentStatus.FAILED,
            PaymentStatus.CANCELLED
        ]

    @property
    def used_card(self) -> bool:
        return self.payment_method == PaymentMethod.CARD

    @property
    def processing_time_seconds(self) -> Optional[int]:
        if self.completed_at and self.created_at:
            delta = self.completed_at - self.created_at
            return int(delta.total_seconds())
        return None

    def __repr__(self) -> str:
        return (
            f"<Payment(id={self.id}, user_id={self.user_id}, "
            f"type={self.payment_type}, amount={self.amount} BYN, "
            f"status={self.status})>"
        )

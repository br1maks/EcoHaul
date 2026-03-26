from typing import Optional
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import String, Integer, ForeignKey, DateTime, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, IDMixin, TimestampMixin, SoftDeleteMixin
from .enums import SubscriptionTier

class Subscription(Base, IDMixin, TimestampMixin, SoftDeleteMixin):

    __tablename__ = "subscriptions"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    tier: Mapped[SubscriptionTier] = mapped_column(
        String(20),
        nullable=False,
        default=SubscriptionTier.FREE,
    )

    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    end_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    renewed_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    auto_renew_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="Включено ли автоматическое продление подписки"
    )

    yookassa_payment_method_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="ID сохранённого способа оплаты в ЮKassa для автопродления"
    )

    next_billing_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Дата следующего автоматического списания (если автопродление включено)"
    )

    last_payment_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID последнего успешного платежа за эту подписку"
    )

    user = relationship(
        "User",
        back_populates="subscription",
    )

    payments = relationship(
        "Payment",
        back_populates="subscription",
        foreign_keys="[Payment.subscription_id]",
        doc="История платежей за подписку"
    )

    __table_args__ = (
        Index("idx_subscription_user_id", "user_id"),
        Index("idx_subscription_is_active", "is_active"),
        Index("idx_subscription_end_date", "end_date"),
        Index("idx_subscription_tier_active", "tier", "is_active"),
        Index("idx_subscription_auto_renew", "auto_renew_enabled", "next_billing_date"),
    )

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.end_date

    @property
    def is_valid(self) -> bool:
        return self.is_active and not self.is_expired

    @property
    def discount_percentage(self) -> float:
        if not self.is_valid:
            return 0.0

        discount_map = {
            SubscriptionTier.FREE: 0.0,
            SubscriptionTier.BASIC: 20.0,
            SubscriptionTier.PREMIUM: 30.0
        }

        return discount_map.get(self.tier, 0.0)

    @property
    def days_remaining(self) -> int:
        if self.is_expired:
            return 0

        now = datetime.now(timezone.utc)
        delta = self.end_date - now
        return max(0, delta.days)

    @property
    def is_expiring_soon(self) -> bool:
        return 0 < self.days_remaining <= 7

    def __repr__(self) -> str:
        return (
            f"<Subscription(id={self.id}, user_id={self.user_id}, "
            f"tier={self.tier}, is_valid={self.is_valid}, "
            f"days_remaining={self.days_remaining})>"
        )

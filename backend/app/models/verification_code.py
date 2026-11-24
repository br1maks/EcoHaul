from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import String, Integer, BigInteger, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, IDMixin, TimestampMixin

class VerificationCode(Base, IDMixin, TimestampMixin):
    __tablename__ = "verification_codes"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Пользователь которому принадлежит код"
    )

    code_digest: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="HMAC digest bound to the user, purpose and challenge id"
    )

    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        doc="Email на который отправлен код (если используется email)"
    )

    telegram_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        index=True,
        doc="Telegram ID куда отправлен код (если используется Telegram)"
    )

    purpose: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Назначение кода: account_verification, password_reset, 2fa"
    )

    is_used: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Использован ли код"
    )

    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Время использования кода"
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="Время истечения кода (обычно +15 минут)"
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Количество попыток ввода кода"
    )

    max_attempts: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
        doc="Максимальное количество попыток"
    )

    user = relationship("User", back_populates="verification_codes")

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_valid(self) -> bool:
        return (
            not self.is_used
            and not self.is_expired
            and self.attempts < self.max_attempts
        )

    def increment_attempts(self):
        self.attempts += 1

    def mark_as_used(self):
        self.is_used = True
        self.used_at = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return f"<VerificationCode(id={self.id}, purpose={self.purpose}, is_valid={self.is_valid})>"

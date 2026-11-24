"""Durable delivery intents committed with the business change they describe."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Identity, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class OutboxMessage(Base):
    __tablename__ = "outbox_messages"

    sequence: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    event_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), default=uuid4, unique=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    stream: Mapped[str] = mapped_column(String(200), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    discarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    discard_reason: Mapped[str | None] = mapped_column(String(200))
    last_error: Mapped[str | None] = mapped_column(String(100))

    __table_args__ = (
        CheckConstraint("channel IN ('websocket', 'telegram', 'cache')", name="ck_outbox_channel"),
        CheckConstraint("attempts >= 0", name="ck_outbox_attempts"),
        CheckConstraint(
            "delivered_at IS NULL OR discarded_at IS NULL", name="ck_outbox_terminal_state"
        ),
        Index(
            "ix_outbox_ready",
            "channel",
            "available_at",
            "sequence",
            postgresql_where=delivered_at.is_(None) & discarded_at.is_(None),
        ),
        Index(
            "ix_outbox_stream",
            "channel",
            "stream",
            "sequence",
            postgresql_where=delivered_at.is_(None) & discarded_at.is_(None),
        ),
    )

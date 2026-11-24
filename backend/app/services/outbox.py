"""No transport calls here: producers only add rows to their current transaction."""
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.outbox import OutboxMessage


def queue_websocket(
    db: AsyncSession, user_id: UUID, message: dict, *, aggregate_key: str = "user"
) -> None:
    db.add(
        OutboxMessage(
            channel="websocket",
            stream=f"{aggregate_key}:{user_id}",
            payload=jsonable_encoder({"user_id": user_id, "message": message}),
        )
    )


def queue_telegram(
    db: AsyncSession, telegram_id: int | None, text: str, *, aggregate_key: str = "user"
) -> None:
    # Local/demo mode must never accumulate real outbound messages to send later.
    if settings.TELEGRAM_ENABLED and telegram_id:
        db.add(
            OutboxMessage(
                channel="telegram",
                stream=f"{aggregate_key}:{telegram_id}",
                payload={"telegram_id": telegram_id, "text": text},
            )
        )


def invalidate_available_orders(db: AsyncSession) -> None:
    db.add(
        OutboxMessage(
            channel="cache", stream="orders:available", payload={"key": "orders:available"}
        )
    )

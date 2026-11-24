"""Single-API-process dispatcher; transport success is not an end-user acknowledgement."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from aiogram import Bot
from sqlalchemy import exists, select
from sqlalchemy.orm import aliased

from app.core.config import settings
from app.core.database import async_session_maker
from app.core.redis import get_redis
from app.models.outbox import OutboxMessage
from app.models.notification import Notification
from app.websocket.connection_manager import manager

logger = logging.getLogger(__name__)
CHANNELS = ("websocket", "telegram", "cache")
DELIVERY_TIMEOUT_SECONDS = 10


async def deliver(message: OutboxMessage) -> None:
    payload = message.payload
    if message.channel == "websocket":
        await manager.send_personal_message(
            UUID(payload["user_id"]),
            {
                **payload["message"],
                "event_id": str(message.event_id),
            },
        )
    elif message.channel == "telegram":
        bot = Bot(token=settings.BOT_TOKEN)
        try:
            await bot.send_message(chat_id=payload["telegram_id"], text=payload["text"])
        finally:
            await bot.session.close()
    elif message.channel == "cache":
        await get_redis().delete(payload["key"])
    else:
        raise ValueError("Unknown outbox channel")


async def dispatch_one(channel: str) -> bool:
    """Hold only an outbox-row lock during bounded I/O, never an order/user lock.

    Pending earlier rows block their own stream even during backoff. A concurrent
    dispatcher skips a locked head without overtaking it through a later row.
    """
    if channel == "telegram" and not settings.TELEGRAM_ENABLED:
        return False
    earlier = aliased(OutboxMessage)
    blocked = exists(
        select(earlier.sequence).where(
            earlier.channel == OutboxMessage.channel,
            earlier.stream == OutboxMessage.stream,
            earlier.sequence < OutboxMessage.sequence,
            earlier.delivered_at.is_(None),
            earlier.discarded_at.is_(None),
        )
    )
    async with async_session_maker() as db:
        async with db.begin():
            message = await db.scalar(
                select(OutboxMessage)
                .where(
                    OutboxMessage.channel == channel,
                    OutboxMessage.delivered_at.is_(None),
                    OutboxMessage.discarded_at.is_(None),
                    OutboxMessage.available_at <= datetime.now(timezone.utc),
                    ~blocked,
                )
                .order_by(OutboxMessage.sequence)
                .limit(1)
                .with_for_update(skip_locked=True, of=OutboxMessage)
            )
            if message is None:
                return False
            message.attempts += 1
            try:
                async with asyncio.timeout(DELIVERY_TIMEOUT_SECONDS):
                    relevant = True
                    if message.channel == "websocket":
                        envelope = message.payload["message"]
                        data = envelope["data"]
                        notification_id = data.get("notification_id")
                        if envelope["type"] == "NEW_NOTIFICATION":
                            notification_id = data.get("id")
                        if notification_id:
                            relevant = (
                                await db.scalar(
                                    select(Notification.id).where(
                                        Notification.id == UUID(notification_id),
                                        Notification.user_id == UUID(message.payload["user_id"]),
                                    )
                                )
                                is not None
                            )
                    # Deleting an inbox entry must not resurrect it through an old
                    # undelivered realtime hint. Current order state still comes from HTTP.
                    if relevant:
                        await deliver(message)
            except Exception as exc:
                # Exception bodies can contain Telegram URLs/tokens or private payloads.
                message.last_error = type(exc).__name__[:100]
                delay = min(300, 2 ** min(message.attempts, 9))
                message.available_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
                logger.warning(
                    "Outbox retry event=%s channel=%s attempt=%s error=%s",
                    message.event_id,
                    channel,
                    message.attempts,
                    message.last_error,
                )
            else:
                message.delivered_at = datetime.now(timezone.utc)
                message.last_error = None
    return True


async def dispatch_forever(channel: str) -> None:
    while True:
        try:
            processed = await dispatch_one(channel)
        except Exception as exc:
            # A lost commit leaves the row pending; retries reuse the same event id.
            logger.warning("Outbox unavailable channel=%s error=%s", channel, type(exc).__name__)
            processed = False
        if not processed:
            await asyncio.sleep(1)

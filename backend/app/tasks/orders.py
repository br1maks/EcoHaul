import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.celery_app import celery_app
from app.core.database import async_session_maker
from app.models.order import Order
from app.models.user import User
from app.models.enums import OrderStatus
from app.services.outbox import queue_telegram, invalidate_available_orders
from app.services.order_events import queue_order_update
from app.websocket.schemas import create_order_status_message

logger = logging.getLogger(__name__)

@celery_app.task
def auto_cancel_expired_orders() -> None:
    asyncio.run(_cancel_expired())

async def _cancel_expired() -> None:
    now = datetime.now(timezone.utc)

    async with async_session_maker() as db:
        stmt = select(Order).where(
            Order.status == OrderStatus.PENDING,
            Order.expires_at < now,
        ).with_for_update(skip_locked=True, of=Order)
        result = await db.execute(stmt)
        expired_orders = result.scalars().all()

        if not expired_orders:
            logger.info("Просроченных заказов не найдено")
            return

        cancelled_count = 0
        for order in expired_orders:
            order.status = OrderStatus.CANCELLED
            order.cancelled_at = now
            order.cancellation_reason = "Заказ отменён автоматически — истёк срок ожидания"
            queue_order_update(db, order.client_id, create_order_status_message(
                order.id, "CANCELLED", order.cancellation_reason, old_status="PENDING"))
            cancelled_count += 1

            if order.client_id:
                client_stmt = select(User).where(User.id == order.client_id)
                client_result = await db.execute(client_stmt)
                client = client_result.scalar_one_or_none()
                if client and client.telegram_id:
                    queue_telegram(db,
                        client.telegram_id,
                        f"Ваш заказ #{str(order.id)[:8]}... отменён — "
                        "никто из курьеров не взял его вовремя. "
                        "Попробуйте создать новый заказ.", aggregate_key=f"order:{order.id}"
                    )

        invalidate_available_orders(db)
        await db.commit()
        logger.info(f"Автоотмена: отменено {cancelled_count} просроченных заказов")

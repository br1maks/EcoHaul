import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.celery_app import celery_app
from app.core.database import async_session_maker
from app.models.subscription import Subscription
from app.models.user import User

logger = logging.getLogger(__name__)

@celery_app.task
def check_expired_subscriptions() -> None:
    asyncio.run(_deactivate_expired())

async def _deactivate_expired() -> None:
    now = datetime.now(timezone.utc)

    async with async_session_maker() as db:
        stmt = select(Subscription).where(
            Subscription.is_active == True,
            Subscription.end_date < now,
        )
        result = await db.execute(stmt)
        expired = result.scalars().all()

        if not expired:
            logger.info("Просроченных подписок не найдено")
            return

        count = 0
        for sub in expired:
            sub.is_active = False
            count += 1

            user_stmt = select(User).where(User.id == sub.user_id)
            user_result = await db.execute(user_stmt)
            user = user_result.scalar_one_or_none()

            if user and user.telegram_id:
                from app.tasks.notifications import notify_user
                notify_user.delay(
                    user.telegram_id,
                    "Ваша подписка истекла.\n"
                    "Откройте приложение, чтобы продлить её и сохранить скидки."
                )

        await db.commit()
        logger.info(f"Деактивировано просроченных подписок: {count}")

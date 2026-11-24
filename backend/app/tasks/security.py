import asyncio
from datetime import datetime, timedelta, timezone

from app.celery_app import celery_app
from app.core.database import async_session_maker
from app.models import AuthAttemptBucket, AuthSession, VerificationCode, WebSocketTicket
from sqlalchemy import delete, or_


async def _cleanup():
    instant = datetime.now(timezone.utc)
    async with async_session_maker() as db:
        await db.execute(
            delete(WebSocketTicket).where(WebSocketTicket.expires_at < instant - timedelta(hours=1))
        )
        await db.execute(
            delete(AuthAttemptBucket).where(
                AuthAttemptBucket.window_started_at < instant - timedelta(days=1)
            )
        )
        await db.execute(
            delete(AuthSession).where(
                or_(
                    AuthSession.expires_at < instant - timedelta(days=30),
                    AuthSession.revoked_at < instant - timedelta(days=30),
                )
            )
        )
        await db.execute(
            delete(VerificationCode).where(
                VerificationCode.expires_at < instant - timedelta(days=30)
            )
        )
        await db.commit()


@celery_app.task
def cleanup_security_records():
    asyncio.run(_cleanup())

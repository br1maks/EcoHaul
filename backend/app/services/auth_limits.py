"""Atomic account/IP budgets; failures cannot roll them back with the request."""
import hashlib
import hmac
import math
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.core.database import async_session_maker
from app.models.auth_session import AuthAttemptBucket
from fastapi import HTTPException
from sqlalchemy import case
from sqlalchemy.dialects.postgresql import insert


async def reserve_attempt(scope: str, identity: str, *, limit: int, seconds: int):
    key = hmac.new(
        settings.SECRET_KEY.encode(), f"{scope}:{identity}".encode(), hashlib.sha256
    ).hexdigest()
    instant = datetime.now(timezone.utc)
    expired = AuthAttemptBucket.window_started_at <= instant - timedelta(seconds=seconds)
    statement = (
        insert(AuthAttemptBucket)
        .values(key_digest=key, scope=scope, attempts=1, window_started_at=instant)
        .on_conflict_do_update(
            index_elements=["key_digest"],
            set_={
                "attempts": case((expired, 1), else_=AuthAttemptBucket.attempts + 1),
                "window_started_at": case(
                    (expired, instant), else_=AuthAttemptBucket.window_started_at
                ),
            },
        )
        .returning(AuthAttemptBucket.attempts, AuthAttemptBucket.window_started_at)
    )
    async with async_session_maker() as db:
        attempts, started = (await db.execute(statement)).one()
        await db.commit()
    if attempts > limit:
        retry = max(1, math.ceil((started + timedelta(seconds=seconds) - instant).total_seconds()))
        raise HTTPException(
            status_code=429,
            detail="Слишком много попыток. Повторите позже",
            headers={"Retry-After": str(retry)},
        )

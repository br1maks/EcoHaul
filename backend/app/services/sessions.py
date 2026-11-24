import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from app.core.config import settings
from app.core.security import create_tokens, decode_token
from app.models import AuthSession, User, WebSocketTicket
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession


def now():
    return datetime.now(timezone.utc)


def digest(token: str):
    return hashlib.sha256(token.encode()).hexdigest()


async def issue_session(db: AsyncSession, user: User, *, verified_password_hash: str | None = None):
    # Session creation, refresh and account-wide revocation serialize on the user.
    # Re-read after waiting: a concurrent password reset/block must win over stale login data.
    await db.flush()
    user = await db.scalar(
        select(User)
        .where(User.id == user.id)
        .execution_options(populate_existing=True)
        .with_for_update(of=User)
    )
    if user is None or not user.is_active:
        raise HTTPException(status_code=403, detail="Пользователь недоступен")
    if verified_password_hash is not None and user.password_hash != verified_password_hash:
        raise HTTPException(status_code=401, detail="Данные входа изменились. Войдите заново")
    session = AuthSession(
        id=uuid4(),
        user_id=user.id,
        expires_at=now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    tokens = create_tokens(str(user.id), user.role, session.id, session.expires_at)
    session.refresh_digest = digest(tokens["refresh_token"])
    db.add(session)
    return tokens


async def rotate_session(db: AsyncSession, token: str):
    payload = decode_token(token)
    try:
        if not payload or payload.get("type") != "refresh":
            raise ValueError()
        user_id, session_id = UUID(payload["sub"]), UUID(payload["sid"])
    except (KeyError, ValueError, TypeError, AttributeError):
        raise HTTPException(status_code=401, detail="Невалидный refresh-токен")
    await db.execute(select(User).where(User.id == user_id).with_for_update(of=User))
    user = await db.get(User, user_id)
    session = await db.scalar(
        select(AuthSession)
        .where(AuthSession.id == session_id, AuthSession.user_id == user_id)
        .with_for_update(of=AuthSession)
    )
    if user is None or session is None or session.revoked_at or session.expires_at <= now():
        raise HTTPException(status_code=401, detail="Сессия завершена. Войдите заново")
    if not user.is_active:
        session.revoked_at = now()
        await db.commit()
        raise HTTPException(status_code=403, detail="Пользователь заблокирован")
    if not hmac.compare_digest(session.refresh_digest, digest(token)):
        session.revoked_at = now()
        await db.commit()  # replay revocation must survive the HTTP error/rollback
        raise HTTPException(
            status_code=401, detail="Повторное использование refresh-токена. Войдите заново"
        )
    tokens = create_tokens(str(user.id), user.role, session.id, session.expires_at)
    session.refresh_digest = digest(tokens["refresh_token"])
    session.last_used_at = now()
    await db.commit()
    return tokens


async def validate_access(db: AsyncSession, token: str):
    payload = decode_token(token)
    try:
        if not payload or payload.get("type") != "access":
            raise ValueError()
        user_id, session_id = UUID(payload["sub"]), UUID(payload["sid"])
    except (KeyError, ValueError, TypeError, AttributeError):
        raise HTTPException(status_code=401, detail="Не удалось проверить сессию")
    session = await db.get(AuthSession, session_id, populate_existing=True)
    user = await db.get(User, user_id, populate_existing=True)
    if (
        not session
        or session.user_id != user_id
        or session.revoked_at
        or session.expires_at <= now()
        or not user
    ):
        raise HTTPException(status_code=401, detail="Сессия завершена")
    return user, session


async def revoke_user_sessions(db: AsyncSession, user_id: UUID):
    await db.execute(select(User).where(User.id == user_id).with_for_update(of=User))
    await db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=now())
    )


async def issue_websocket_ticket(db: AsyncSession, session_id: UUID, access_token: str):
    payload = decode_token(access_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Сессия завершена")
    ticket = secrets.token_urlsafe(32)
    db.add(
        WebSocketTicket(
            ticket_digest=digest(ticket),
            session_id=session_id,
            expires_at=now() + timedelta(seconds=30),
            access_expires_at=datetime.fromtimestamp(payload["exp"], timezone.utc),
        )
    )
    await db.commit()
    return ticket


async def validate_socket_session(session_id: UUID, access_expires_at: datetime):
    if access_expires_at <= now():
        raise ValueError("Access credential expired")
    from app.core.database import async_session_maker

    async with async_session_maker() as db:
        session = await db.get(AuthSession, session_id)
        user = await db.get(User, session.user_id) if session else None
        if (
            not session
            or session.revoked_at
            or session.expires_at <= now()
            or not user
            or not user.is_active
        ):
            raise ValueError("Session unavailable")
        return user.id


async def consume_websocket_ticket(ticket: str):
    from app.core.database import async_session_maker

    async with async_session_maker() as db:
        record = await db.scalar(
            update(WebSocketTicket)
            .where(
                WebSocketTicket.ticket_digest == digest(ticket),
                WebSocketTicket.used_at.is_(None),
                WebSocketTicket.expires_at > now(),
            )
            .values(used_at=now())
            .returning(WebSocketTicket)
        )
        if record is None:
            raise ValueError("Ticket unavailable")
        session_id, access_deadline = record.session_id, record.access_expires_at
        await db.commit()
    user_id = await validate_socket_session(session_id, access_deadline)
    return user_id, session_id, access_deadline

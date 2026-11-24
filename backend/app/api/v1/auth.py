import asyncio
from datetime import datetime
from uuid import UUID

from app.api.dependencies import get_current_active_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    PASSWORD_PREFIX,
    decode_token,
    hash_password,
    validate_telegram_init_data,
    verify_password,
)
from app.models.auth_session import AuthSession
from app.models.enums import CourierStatus, UserRole
from app.models.user import User
from app.services.auth_limits import reserve_attempt
from app.services.sessions import (
    issue_session,
    issue_websocket_ticket,
    now,
    revoke_user_sessions,
    rotate_session,
)
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


class TelegramAuthRequest(BaseModel):
    init_data: str = Field(min_length=1, max_length=16384)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str = Field(min_length=1, max_length=4096)
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=4096)


class AdminLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=512)


class SessionResponse(BaseModel):
    id: UUID
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    current: bool


class WebSocketTicketResponse(BaseModel):
    ticket: str
    expires_in: int


class TestAuthRequest(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    age: int | None = None
    role: UserRole | None = None
    courier_status: CourierStatus | None = None
    is_verified: bool | None = None
    passport_number: str | None = None
    password: str | None = Field(None, min_length=4, max_length=512)


router = APIRouter(prefix="/auth", tags=["Авторизация"])
DUMMY_PASSWORD_HASH = hash_password("dummy-comparison-only-not-an-account")


@router.post("/telegram", response_model=TokenResponse)
async def telegram_auth(
    data: TelegramAuthRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    await reserve_attempt(
        "telegram_ip", request.client.host if request.client else "unknown", limit=30, seconds=900
    )
    valid, profile, error = validate_telegram_init_data(
        data.init_data, settings.TELEGRAM_AUTH_MAX_AGE_SECONDS
    )
    if not valid or not profile:
        raise HTTPException(status_code=401, detail=error or "Нет данных пользователя")
    await reserve_attempt("telegram_account", str(profile["id"]), limit=10, seconds=900)
    statement = select(User).where(User.telegram_id == profile["id"])
    user = await db.scalar(statement)
    if user is None:
        try:
            async with db.begin_nested():
                user = User(
                    telegram_id=profile["id"],
                    first_name=profile.get("first_name") or "",
                    last_name=profile.get("last_name") or "",
                    telegram_username=profile.get("username"),
                    role=UserRole.CLIENT,
                )
                db.add(user)
                await db.flush()
        except IntegrityError:
            user = await db.scalar(statement)
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Пользователь заблокирован")
    user.first_name = profile.get("first_name") or user.first_name
    user.last_name = profile.get("last_name") or user.last_name
    user.telegram_username = profile.get("username")
    tokens = await issue_session(db, user)
    await db.commit()
    return TokenResponse(**tokens)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    return TokenResponse(**await rotate_session(db, data.refresh_token))


@router.post("/test", response_model=TokenResponse)
async def test_auth(
    data: TestAuthRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    if not (settings.DEBUG and settings.ENABLE_DEV_AUTH):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )
    stmt = select(User).where(User.telegram_id == data.telegram_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        try:
            user = User(
                telegram_id=data.telegram_id,
                first_name=data.first_name,
                last_name=data.last_name or "",
                telegram_username=data.username,
                email=data.email,
                phone=data.phone,
                age=data.age,
                role=data.role or UserRole.CLIENT,
                courier_status=data.courier_status,
                is_verified=data.is_verified or False,
                passport_number=data.passport_number,
                password_hash=hash_password(data.password) if data.password else None,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        except IntegrityError:
            await db.rollback()
            result = await db.execute(stmt)
            user = result.scalar_one()
    else:
        user.first_name = data.first_name
        user.last_name = data.last_name or user.last_name
        user.telegram_username = data.username or user.telegram_username
        user.email = data.email or user.email
        user.phone = data.phone or user.phone
        if data.age is not None:
            user.age = data.age
        if data.role is not None:
            user.role = data.role
        if data.courier_status is not None:
            user.courier_status = data.courier_status
        if data.is_verified is not None:
            user.is_verified = data.is_verified
        if data.passport_number is not None:
            user.passport_number = data.passport_number
        if data.password is not None:
            user.password_hash = hash_password(data.password)
        await db.commit()

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Пользователь заблокирован")
    tokens = await issue_session(db, user)
    await db.commit()
    return TokenResponse(**tokens)


@router.post("/admin/login", response_model=TokenResponse)
async def admin_login(
    data: AdminLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    identity = data.email.strip().lower()
    await reserve_attempt(
        "admin_ip", request.client.host if request.client else "unknown", limit=30, seconds=900
    )
    await reserve_attempt("admin_account", identity, limit=5, seconds=900)
    stmt = select(User).where(func.lower(User.email) == identity)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or user.password_hash is None:
        await asyncio.to_thread(verify_password, data.password, DUMMY_PASSWORD_HASH)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    if not await asyncio.to_thread(verify_password, data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещён",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь заблокирован",
        )

    verified_hash = user.password_hash
    tokens = await issue_session(db, user, verified_password_hash=verified_hash)
    if not verified_hash.startswith(PASSWORD_PREFIX):
        user.password_hash = await asyncio.to_thread(hash_password, data.password)
    await db.commit()
    return TokenResponse(**tokens)


@router.post("/logout", status_code=204)
async def logout(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(data.refresh_token)
    try:
        if not payload or payload.get("type") != "refresh":
            raise ValueError()
        session_id, user_id = UUID(payload["sid"]), UUID(payload["sub"])
    except (KeyError, ValueError, TypeError, AttributeError):
        raise HTTPException(status_code=401, detail="Невалидная сессия")
    session = await db.scalar(
        select(AuthSession)
        .where(AuthSession.id == session_id, AuthSession.user_id == user_id)
        .with_for_update(of=AuthSession)
    )
    if session is None:
        return
    session.revoked_at = now()
    await db.commit()


@router.post("/ws-ticket", response_model=WebSocketTicketResponse)
async def websocket_ticket(
    request: Request,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await db.commit()
    await reserve_attempt("websocket_ticket", str(user.id), limit=60, seconds=60)
    ticket = await issue_websocket_ticket(
        db, request.state.auth_session_id, request.headers["authorization"].split(" ", 1)[1]
    )
    return {"ticket": ticket, "expires_in": 30}


@router.post("/logout-all", status_code=204)
async def logout_all(
    user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)
):
    await revoke_user_sessions(db, user.id)
    await db.commit()


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    request: Request,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    sessions = (
        await db.scalars(
            select(AuthSession)
            .where(
                AuthSession.user_id == user.id,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now(),
            )
            .order_by(AuthSession.created_at.desc())
        )
    ).all()
    return [
        {
            "id": item.id,
            "created_at": item.created_at,
            "last_used_at": item.last_used_at,
            "expires_at": item.expires_at,
            "current": item.id == request.state.auth_session_id,
        }
        for item in sessions
    ]


@router.delete("/sessions/{session_id}", status_code=204)
async def revoke_session(
    session_id: UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    session = await db.scalar(
        select(AuthSession)
        .where(AuthSession.id == session_id, AuthSession.user_id == user.id)
        .with_for_update(of=AuthSession)
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    session.revoked_at = now()
    await db.commit()

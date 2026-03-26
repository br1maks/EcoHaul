from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.core.security import (
    validate_telegram_init_data,
    create_tokens,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.models.enums import UserRole, CourierStatus

class TelegramAuthRequest(BaseModel):
    init_data: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class AdminLoginRequest(BaseModel):
    email: str
    password: str

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
    password: str | None = Field(None, min_length=4, max_length=72)

router = APIRouter(prefix="/auth", tags=["Авторизация"])

@router.post("/telegram", response_model=TokenResponse)
async def telegram_auth(
    data: TelegramAuthRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    is_valid, user_data, error = validate_telegram_init_data(data.init_data)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error,
        )

    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Нет данных пользователя",
        )

    telegram_id = user_data["id"]
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_id=telegram_id,
            first_name=user_data.get("first_name", ""),
            last_name=user_data.get("last_name", ""),
            telegram_username=user_data.get("username"),
            role=UserRole.CLIENT,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        user.first_name = user_data.get("first_name", user.first_name)
        user.last_name = user_data.get("last_name", user.last_name)
        user.telegram_username = user_data.get("username")
        await db.commit()

    tokens = create_tokens(str(user.id), user.role)
    return TokenResponse(**tokens)

@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    payload = decode_token(data.refresh_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный токен",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный тип токена",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный токен",
        )

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь заблокирован",
        )

    tokens = create_tokens(str(user.id), user.role)
    return TokenResponse(**tokens)

@router.post("/test", response_model=TokenResponse)
async def test_auth(
    data: TestAuthRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    if not settings.DEBUG:
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

    tokens = create_tokens(str(user.id), user.role)
    return TokenResponse(**tokens)

@router.post("/admin/login", response_model=TokenResponse)
async def admin_login(
    data: AdminLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    stmt = select(User).where(User.email == data.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or user.password_hash is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    if not verify_password(data.password, user.password_hash):
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

    tokens = create_tokens(str(user.id), user.role)
    return TokenResponse(**tokens)

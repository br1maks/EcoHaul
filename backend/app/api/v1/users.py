from typing import Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import hash_password
from app.services.sessions import revoke_user_sessions
from app.api.dependencies import get_current_active_user, require_admin
from app.models.user import User
from app.models.enums import UserRole, CourierStatus

class UserResponse(BaseModel):
    id: UUID
    telegram_id: int
    telegram_username: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    first_name: str
    last_name: str
    age: Optional[int] = None
    role: UserRole
    courier_status: Optional[CourierStatus] = None
    rating: float
    total_orders: int
    completed_orders: int
    is_verified: bool
    is_active: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    age: Optional[int] = Field(None, ge=14, le=120)
    password: Optional[str] = Field(None, min_length=15, max_length=512, description="Новый пароль: от 15 до 512 символов")
    courier_status: Optional[CourierStatus] = Field(None, description="Статус курьера (только для курьеров)")

class AdminUserUpdate(BaseModel):
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=20)
    email: Optional[str] = Field(default=None, max_length=255)
    age: Optional[int] = Field(default=None, ge=14, le=120)
    role: Optional[UserRole] = Field(default=None, description="Роль пользователя")
    courier_status: Optional[CourierStatus] = Field(default=None, description="Статус курьера")
    is_verified: Optional[bool] = Field(default=None, description="Верифицирован ли пользователь")
    is_active: Optional[bool] = Field(default=None, description="Активен ли пользователя")

class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    size: int
    pages: int

router = APIRouter(prefix="/users", tags=["Пользователи"])

@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_active_user),
):
    return current_user

@router.patch("/me", response_model=UserResponse)
async def update_me(
    data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    update_data = data.model_dump(exclude_unset=True)

    if "password" in update_data:
        password = update_data.pop("password")
        if password is None:
            raise HTTPException(status_code=422, detail="Укажите пароль")
        current_user.password_hash = hash_password(password)
        await db.flush()
        await revoke_user_sessions(db, current_user.id)

    for field, value in update_data.items():
        setattr(current_user, field, value)

    await db.commit()
    await db.refresh(current_user)

    return current_user

@router.get("/clients/list", response_model=list[UserResponse])
async def get_clients_list(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).where(User.role == UserRole.CLIENT).order_by(User.first_name)
    result = await db.execute(stmt)
    users = result.scalars().all()
    return users

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    return user

@router.patch("/{user_id}", response_model=UserResponse)
async def update_user_by_admin(
    user_id: UUID,
    data: AdminUserUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    if update_data.get("is_active") is False:
        await db.flush()
        await revoke_user_sessions(db, user.id)
    await db.commit()
    await db.refresh(user)
    return user

@router.get("", response_model=UserListResponse)
async def get_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    count_stmt = select(func.count()).select_from(User)
    total = await db.scalar(count_stmt) or 0

    offset = (page - 1) * size
    stmt = select(User).offset(offset).limit(size)
    result = await db.execute(stmt)
    users = result.scalars().all()

    pages = (total + size - 1) // size

    return UserListResponse(
        items=users,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )

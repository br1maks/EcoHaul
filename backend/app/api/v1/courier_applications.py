from typing import Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.services.outbox import queue_telegram

from app.core.database import get_db
from app.api.dependencies import require_admin, get_current_active_user
from app.models import (
    User,
    CourierApplication,
    CourierApplicationStatus,
    UserRole,
    CourierStatus,
)

class CourierApplicationCreate(BaseModel):
    phone: str = Field(..., min_length=10, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    has_transport: bool = False
    transport_type: Optional[str] = Field(None, max_length=100)
    work_area: Optional[str] = Field(None, max_length=255)
    message: Optional[str] = Field(None, max_length=1000)

class CourierApplicationResponse(BaseModel):
    id: UUID
    user_id: UUID
    phone: str
    email: Optional[str] = None
    has_transport: bool
    transport_type: Optional[str] = None
    work_area: Optional[str] = None
    message: Optional[str] = None
    status: CourierApplicationStatus
    admin_comment: Optional[str] = None
    reviewed_by_id: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    user_first_name: Optional[str] = None
    user_last_name: Optional[str] = None
    user_telegram_id: Optional[int] = None
    user_telegram_username: Optional[str] = None

    model_config = {"from_attributes": True}

class CourierApplicationReview(BaseModel):
    status: CourierApplicationStatus = Field(..., description="APPROVED или REJECTED")
    admin_comment: Optional[str] = Field(None, max_length=500)

class CourierApplicationListResponse(BaseModel):
    items: list[CourierApplicationResponse]
    total: int
    page: int
    size: int
    pages: int

router = APIRouter(prefix="/courier-applications", tags=["Заявки на курьера"])

@router.post("", response_model=CourierApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
    data: CourierApplicationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    user = current_user

    if user.role == UserRole.COURIER:
        raise HTTPException(status_code=400, detail="Вы уже являетесь курьером")

    existing_stmt = select(CourierApplication).where(
        CourierApplication.user_id == user.id,
        CourierApplication.status == CourierApplicationStatus.PENDING
    )
    existing = await db.execute(existing_stmt)
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="У вас уже есть активная заявка на рассмотрении")

    application = CourierApplication(
        user_id=user.id,
        phone=data.phone,
        email=data.email,
        has_transport=data.has_transport,
        transport_type=data.transport_type,
        work_area=data.work_area,
        message=data.message,
        status=CourierApplicationStatus.PENDING,
    )

    db.add(application)
    await db.commit()
    await db.refresh(application)

    return CourierApplicationResponse(
        id=application.id,
        user_id=application.user_id,
        phone=application.phone,
        email=application.email,
        has_transport=application.has_transport,
        transport_type=application.transport_type,
        work_area=application.work_area,
        message=application.message,
        status=application.status,
        admin_comment=application.admin_comment,
        reviewed_by_id=application.reviewed_by_id,
        reviewed_at=application.reviewed_at,
        created_at=application.created_at,
        user_first_name=user.first_name,
        user_last_name=user.last_name,
        user_telegram_id=user.telegram_id,
        user_telegram_username=user.telegram_username,
    )

@router.get("/my", response_model=Optional[CourierApplicationResponse])
async def get_my_application(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    user = current_user

    app_stmt = (
        select(CourierApplication)
        .where(CourierApplication.user_id == user.id)
        .order_by(CourierApplication.created_at.desc())
        .limit(1)
    )
    app_result = await db.execute(app_stmt)
    application = app_result.scalar_one_or_none()

    if not application:
        return None

    return CourierApplicationResponse(
        id=application.id,
        user_id=application.user_id,
        phone=application.phone,
        email=application.email,
        has_transport=application.has_transport,
        transport_type=application.transport_type,
        work_area=application.work_area,
        message=application.message,
        status=application.status,
        admin_comment=application.admin_comment,
        reviewed_by_id=application.reviewed_by_id,
        reviewed_at=application.reviewed_at,
        created_at=application.created_at,
        user_first_name=user.first_name,
        user_last_name=user.last_name,
        user_telegram_id=user.telegram_id,
        user_telegram_username=user.telegram_username,
    )

@router.get("", response_model=CourierApplicationListResponse)
async def get_applications(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status_filter: Optional[CourierApplicationStatus] = Query(None, description="Фильтр по статусу"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    base_query = select(CourierApplication).options(selectinload(CourierApplication.user))

    if status_filter:
        base_query = base_query.where(CourierApplication.status == status_filter)

    count_query = select(func.count()).select_from(CourierApplication)
    if status_filter:
        count_query = count_query.where(CourierApplication.status == status_filter)
    total = await db.scalar(count_query) or 0

    offset = (page - 1) * size
    query = base_query.order_by(CourierApplication.created_at.desc()).offset(offset).limit(size)
    result = await db.execute(query)
    applications = result.scalars().all()

    pages = (total + size - 1) // size

    items = []
    for app in applications:
        items.append(CourierApplicationResponse(
            id=app.id,
            user_id=app.user_id,
            phone=app.phone,
            email=app.email,
            has_transport=app.has_transport,
            transport_type=app.transport_type,
            work_area=app.work_area,
            message=app.message,
            status=app.status,
            admin_comment=app.admin_comment,
            reviewed_by_id=app.reviewed_by_id,
            reviewed_at=app.reviewed_at,
            created_at=app.created_at,
            user_first_name=app.user.first_name if app.user else None,
            user_last_name=app.user.last_name if app.user else None,
            user_telegram_id=app.user.telegram_id if app.user else None,
            user_telegram_username=app.user.telegram_username if app.user else None,
        ))

    return CourierApplicationListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )

@router.get("/pending/count")
async def get_pending_count(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    count = await db.scalar(
        select(func.count()).select_from(CourierApplication).where(
            CourierApplication.status == CourierApplicationStatus.PENDING
        )
    )
    return {"count": count or 0}

@router.patch("/{application_id}/review", response_model=CourierApplicationResponse)
async def review_application(
    application_id: UUID,
    data: CourierApplicationReview,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CourierApplication).options(selectinload(CourierApplication.user)).where(
        CourierApplication.id == application_id
    ).with_for_update(of=CourierApplication)
    result = await db.execute(stmt)
    application = result.scalar_one_or_none()

    if not application:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    if application.status != CourierApplicationStatus.PENDING:
        raise HTTPException(status_code=400, detail="Заявка уже рассмотрена")

    if data.status not in [CourierApplicationStatus.APPROVED, CourierApplicationStatus.REJECTED]:
        raise HTTPException(status_code=400, detail="Статус должен быть APPROVED или REJECTED")

    application.status = data.status
    application.admin_comment = data.admin_comment
    application.reviewed_by_id = current_user.id
    application.reviewed_at = datetime.utcnow()

    if data.status == CourierApplicationStatus.APPROVED:
        user = application.user
        if user:
            user.role = UserRole.COURIER
            user.courier_status = CourierStatus.OFFLINE
            user.is_verified = True
            if application.phone and not user.phone:
                user.phone = application.phone
            if application.email and not user.email:
                user.email = application.email

    if application.user and application.user.telegram_id:
        if data.status == CourierApplicationStatus.APPROVED:
            queue_telegram(db, application.user.telegram_id, "Ваша заявка на курьера одобрена!\nТеперь вы можете принимать заказы.")
        elif data.status == CourierApplicationStatus.REJECTED:
            reason = data.admin_comment or "Причина не указана"
            queue_telegram(db, application.user.telegram_id, f"Ваша заявка на курьера отклонена.\nПричина: {reason}")
    
    
    await db.commit()

    return CourierApplicationResponse(
        id=application.id,
        user_id=application.user_id,
        phone=application.phone,
        email=application.email,
        has_transport=application.has_transport,
        transport_type=application.transport_type,
        work_area=application.work_area,
        message=application.message,
        status=application.status,
        admin_comment=application.admin_comment,
        reviewed_by_id=application.reviewed_by_id,
        reviewed_at=application.reviewed_at,
        created_at=application.created_at,
        user_first_name=application.user.first_name if application.user else None,
        user_last_name=application.user.last_name if application.user else None,
        user_telegram_id=application.user.telegram_id if application.user else None,
        user_telegram_username=application.user.telegram_username if application.user else None,
    )

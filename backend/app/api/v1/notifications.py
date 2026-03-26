from typing import Optional
from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.notification import Notification
from app.models.enums import NotificationType, NotificationChannel
from app.schemas.notification import NotificationResponse, NotificationBrief

router = APIRouter(prefix="/notifications", tags=["Уведомления"])

@router.get("", response_model=list[NotificationResponse])
async def get_my_notifications(
    limit: int = Query(50, ge=1, le=100, description="Количество уведомлений"),
    offset: int = Query(0, ge=0, description="Смещение"),
    is_read: Optional[bool] = Query(None, description="Фильтр: прочитанные/непрочитанные"),
    notification_type: Optional[NotificationType] = Query(None, description="Фильтр по типу"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    filters = [Notification.user_id == current_user.id]

    if is_read is not None:
        filters.append(Notification.is_read == is_read)

    if notification_type is not None:
        filters.append(Notification.notification_type == notification_type)

    stmt = (
        select(Notification)
        .where(and_(*filters))
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(stmt)
    notifications = result.scalars().all()

    return notifications

@router.get("/unread", response_model=list[NotificationBrief])
async def get_unread_notifications(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.is_read == False
        )
        .order_by(Notification.created_at.desc())
    )

    result = await db.execute(stmt)
    notifications = result.scalars().all()

    return notifications

@router.get("/unread/count")
async def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(func.count()).select_from(Notification).where(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    )

    result = await db.execute(stmt)
    unread_count = result.scalar() or 0

    return {"unread_count": unread_count}

@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Notification).where(Notification.id == notification_id)
    result = await db.execute(stmt)
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Уведомление не найдено"
        )

    if notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этому уведомлению"
        )

    return notification

@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_as_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Notification).where(Notification.id == notification_id)
    result = await db.execute(stmt)
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Уведомление не найдено"
        )

    if notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этому уведомлению"
        )

    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
        await db.commit()

    return notification

@router.post("/mark-all-read")
async def mark_all_as_read(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)

    stmt = (
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.is_read == False
        )
        .values(is_read=True, read_at=now)
    )

    result = await db.execute(stmt)
    marked_count: int = result.rowcount
    await db.commit()

    return {"marked_count": marked_count}

@router.delete("/delete-all")
async def delete_all_notifications(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Notification).where(Notification.user_id == current_user.id)
    result = await db.execute(stmt)
    notifications = result.scalars().all()

    deleted_count = len(notifications)

    for notification in notifications:
        await db.delete(notification)

    await db.commit()

    return {"deleted_count": deleted_count}

@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Notification).where(Notification.id == notification_id)
    result = await db.execute(stmt)
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Уведомление не найдено"
        )

    if notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы можете удалить только свои уведомления"
        )

    await db.delete(notification)
    await db.commit()

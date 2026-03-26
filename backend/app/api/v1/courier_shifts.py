
from typing import Optional, cast
from uuid import UUID
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.dependencies import require_courier, require_admin
from app.models.user import User
from app.models.courier_shift import CourierShift
from app.schemas.courier_shift import (
    CourierShiftResponse,
    CourierShiftBrief,
)

router = APIRouter(
    prefix="/courier-shifts",
    tags=["courier-shifts"],
)

@router.post(
    "/start",
    response_model=CourierShiftResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Начать смену",
    description="Курьер начинает новую рабочую смену. Проверяет, что у курьера нет активной смены.",
)
async def start_shift(
    start_location_lat: Optional[float] = None,
    start_location_lon: Optional[float] = None,
    notes: Optional[str] = None,
    current_user: User = Depends(require_courier),
    db: AsyncSession = Depends(get_db),
) -> CourierShiftResponse:

    stmt = select(CourierShift).where(
        and_(
            CourierShift.courier_id == current_user.id,
            CourierShift.ended_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    existing_shift = result.scalar_one_or_none()

    if existing_shift:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="У вас уже есть активная смена. Завершите её перед началом новой.",
        )

    new_shift = CourierShift(
        courier_id=current_user.id,
        started_at=datetime.now(timezone.utc),
        start_location_lat=start_location_lat,
        start_location_lon=start_location_lon,
        notes=notes,
    )

    db.add(new_shift)
    await db.commit()
    await db.refresh(new_shift)

    return CourierShiftResponse.model_validate(new_shift)

@router.post(
    "/end",
    response_model=CourierShiftResponse,
    summary="Завершить смену",
    description="Курьер завершает текущую активную смену.",
)
async def end_shift(
    end_location_lat: Optional[float] = None,
    end_location_lon: Optional[float] = None,
    early_end_reason: Optional[str] = None,
    current_user: User = Depends(require_courier),
    db: AsyncSession = Depends(get_db),
) -> CourierShiftResponse:

    stmt = select(CourierShift).where(
        and_(
            CourierShift.courier_id == current_user.id,
            CourierShift.ended_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    active_shift = result.scalar_one_or_none()

    if not active_shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="У вас нет активной смены",
        )

    active_shift.ended_at = datetime.now(timezone.utc)

    if end_location_lat is not None:
        active_shift.end_location_lat = end_location_lat
    if end_location_lon is not None:
        active_shift.end_location_lon = end_location_lon
    if early_end_reason is not None:
        active_shift.early_end_reason = early_end_reason

    await db.commit()
    await db.refresh(active_shift)

    from app.websocket import manager

    if active_shift.ended_at is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка: ended_at не установлен"
        )

    ended_at: datetime = cast(datetime, active_shift.ended_at)

    ws_message = {
        "type": "SHIFT_ENDED",
        "data": {
            "shift_id": str(active_shift.id),
            "started_at": active_shift.started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "duration_hours": round(active_shift.duration_hours or 0, 2),
            "orders_completed": active_shift.orders_completed,
            "total_distance_km": float(active_shift.total_distance_km),
            "message": f"Смена завершена! Вы выполнили {active_shift.orders_completed} заказов за {round(active_shift.duration_hours or 0, 1)} часов"
        }
    }

    await manager.send_personal_message(current_user.id, ws_message)

    return CourierShiftResponse.model_validate(active_shift)

@router.get(
    "/current",
    response_model=CourierShiftResponse,
    summary="Получить текущую активную смену",
    description="Получить информацию о текущей активной смене курьера.",
)
async def get_current_shift(
    current_user: User = Depends(require_courier),
    db: AsyncSession = Depends(get_db),
) -> CourierShiftResponse:

    stmt = select(CourierShift).where(
        and_(
            CourierShift.courier_id == current_user.id,
            CourierShift.ended_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    active_shift = result.scalar_one_or_none()

    if not active_shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="У вас нет активной смены",
        )

    return CourierShiftResponse.model_validate(active_shift)

@router.get(
    "/history",
    response_model=list[CourierShiftBrief],
    summary="Получить историю смен",
    description="Получить историю всех смен курьера с пагинацией.",
)
async def get_shift_history(
    skip: int = Query(0, ge=0, description="Количество записей для пропуска"),
    limit: int = Query(20, ge=1, le=100, description="Количество записей для получения"),
    current_user: User = Depends(require_courier),
    db: AsyncSession = Depends(get_db),
) -> list[CourierShiftBrief]:

    stmt = (
        select(CourierShift)
        .where(CourierShift.courier_id == current_user.id)
        .order_by(CourierShift.started_at.desc())
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(stmt)
    shifts = result.scalars().all()

    return [CourierShiftBrief.model_validate(shift) for shift in shifts]

@router.get(
    "/daily-stats",
    summary="Получить статистику за день",
    description="Получить статистику курьера за указанную дату (по умолчанию - сегодня).",
)
async def get_daily_stats(
    date: Optional[str] = Query(None, description="Дата в формате YYYY-MM-DD (по умолчанию - сегодня)"),
    current_user: User = Depends(require_courier),
    db: AsyncSession = Depends(get_db),
) -> dict:

    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный формат даты. Используйте YYYY-MM-DD",
            )
    else:
        target_date = datetime.now(timezone.utc).date()

    day_start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    day_end = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=timezone.utc)

    stmt = select(CourierShift).where(
        and_(
            CourierShift.courier_id == current_user.id,
            CourierShift.started_at >= day_start,
            CourierShift.started_at <= day_end,
        )
    )

    result = await db.execute(stmt)
    shifts = result.scalars().all()

    total_shifts = len(shifts)
    total_orders = sum(shift.orders_completed for shift in shifts)
    total_distance = sum(float(shift.total_distance_km) for shift in shifts)

    total_hours = 0.0
    for shift in shifts:
        if shift.ended_at:
            delta = shift.ended_at - shift.started_at
            total_hours += delta.total_seconds() / 3600

    stats = {
        "date": target_date.isoformat(),
        "total_shifts": total_shifts,
        "total_orders": total_orders,
        "total_distance_km": round(total_distance, 2),
        "total_hours": round(total_hours, 2),
        "average_orders_per_hour": round(total_orders / total_hours, 2) if total_hours > 0 else 0,
    }

    return stats

@router.post(
    "/send-daily-stats",
    summary="Отправить ежедневную статистику через WebSocket",
    description="Служебный эндпоинт для отправки ежедневной статистики курьеру (вызывается по расписанию).",
)
async def send_daily_stats_notification(
    courier_id: UUID,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:

    target_date = datetime.now(timezone.utc).date()
    day_start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    day_end = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=timezone.utc)

    stmt = select(CourierShift).where(
        and_(
            CourierShift.courier_id == courier_id,
            CourierShift.started_at >= day_start,
            CourierShift.started_at <= day_end,
        )
    )

    result = await db.execute(stmt)
    shifts = result.scalars().all()

    total_shifts = len(shifts)
    total_orders = sum(shift.orders_completed for shift in shifts)
    total_distance = sum(float(shift.total_distance_km) for shift in shifts)

    total_hours = 0.0
    for shift in shifts:
        if shift.ended_at:
            delta = shift.ended_at - shift.started_at
            total_hours += delta.total_seconds() / 3600

    from app.websocket import manager

    ws_message = {
        "type": "DAILY_STATS",
        "data": {
            "date": target_date.isoformat(),
            "total_shifts": total_shifts,
            "total_orders": total_orders,
            "total_distance_km": round(total_distance, 2),
            "total_hours": round(total_hours, 2),
            "message": f"Статистика за {target_date.strftime('%d.%m.%Y')}: {total_orders} заказов, {round(total_hours, 1)} часов работы, {round(total_distance, 1)} км"
        }
    }

    await manager.send_personal_message(courier_id, ws_message)

    return {"status": "sent", "courier_id": str(courier_id)}

@router.post(
    "/send-shift-reminder",
    summary="Отправить напоминание о начале смены",
    description="Служебный эндпоинт для отправки напоминания курьеру о начале смены (вызывается по расписанию).",
)
async def send_shift_reminder(
    courier_id: UUID,
    shift_start_time: datetime,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:

    from app.models.user import User

    stmt = select(User).where(User.id == courier_id)
    result = await db.execute(stmt)
    courier = result.scalar_one_or_none()

    if not courier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Курьер {courier_id} не найден",
        )

    from app.websocket import manager

    ws_message = {
        "type": "SHIFT_REMINDER",
        "data": {
            "shift_start_time": shift_start_time.isoformat(),
            "courier_name": f"{courier.first_name} {courier.last_name or ''}".strip(),
            "message": f"Напоминание: ваша смена начинается через 30 минут ({shift_start_time.strftime('%H:%M')}). Не забудьте подготовиться!"
        }
    }

    await manager.send_personal_message(courier_id, ws_message)

    return {"status": "sent", "courier_id": str(courier_id), "shift_start_time": shift_start_time.isoformat()}

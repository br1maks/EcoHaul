from app.services.sessions import revoke_user_sessions
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, or_, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import require_admin
from app.models.user import User
from app.models.order import Order
from app.models.address import Address
from app.models.courier_shift import CourierShift
from app.models.review import Review
from app.models.enums import UserRole, OrderStatus, CourierStatus

class AdminStatistics(BaseModel):
    total_users: int
    total_clients: int
    total_couriers: int
    active_couriers: int
    verified_couriers: int

    total_orders: int
    pending_orders: int
    in_progress_orders: int
    completed_orders: int
    cancelled_orders: int
    failed_orders: int

    completion_rate: float = Field(description="Процент выполненных заказов")
    average_order_rating: float = Field(description="Средний рейтинг заказов")

    active_shifts: int
    total_shifts_today: int

class CourierStatistics(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    phone: Optional[str]
    email: Optional[str]

    courier_status: Optional[CourierStatus]
    is_verified: bool
    is_active: bool

    rating: float
    total_orders: int
    completed_orders: int

    active_shift_id: Optional[UUID] = None
    shifts_this_month: int
    total_hours_this_month: float
    orders_this_month: int

class CourierStatisticsList(BaseModel):
    items: list[CourierStatistics]
    total: int
    page: int
    size: int
    pages: int

class ClientStatistics(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    phone: Optional[str]
    email: Optional[str]
    telegram_username: Optional[str]

    total_orders: int
    completed_orders: int
    cancelled_orders: int
    total_spent: float
    average_order_value: float
    last_order_date: Optional[datetime] = None
    subscription_tier: Optional[str] = None
    is_active: bool
    created_at: datetime

class ClientStatisticsList(BaseModel):
    items: list[ClientStatistics]
    total: int
    page: int
    size: int
    pages: int

router = APIRouter(prefix="/admin", tags=["Администрирование"])

@router.get("/statistics", response_model=AdminStatistics)
async def get_admin_statistics(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):

    total_users = await db.scalar(select(func.count()).select_from(User)) or 0
    total_clients = await db.scalar(
        select(func.count()).select_from(User).where(User.role == UserRole.CLIENT)
    ) or 0
    total_couriers = await db.scalar(
        select(func.count()).select_from(User).where(User.role == UserRole.COURIER)
    ) or 0
    active_couriers = await db.scalar(
        select(func.count()).select_from(User).where(
            and_(
                User.role == UserRole.COURIER,
                User.courier_status == CourierStatus.ACTIVE,
                User.is_active.is_(True)
            )
        )
    ) or 0
    verified_couriers = await db.scalar(
        select(func.count()).select_from(User).where(
            and_(
                User.role == UserRole.COURIER,
                User.is_verified.is_(True)
            )
        )
    ) or 0

    total_orders = await db.scalar(select(func.count()).select_from(Order)) or 0
    pending_orders = await db.scalar(
        select(func.count()).select_from(Order).where(Order.status == OrderStatus.PENDING)
    ) or 0
    in_progress_orders = await db.scalar(
        select(func.count()).select_from(Order).where(
            or_(
                Order.status == OrderStatus.ASSIGNED,
                Order.status == OrderStatus.IN_PROGRESS,
                Order.status == OrderStatus.ARRIVED
            )
        )
    ) or 0
    completed_orders = await db.scalar(
        select(func.count()).select_from(Order).where(Order.status == OrderStatus.COMPLETED)
    ) or 0
    cancelled_orders = await db.scalar(
        select(func.count()).select_from(Order).where(Order.status == OrderStatus.CANCELLED)
    ) or 0
    failed_orders = await db.scalar(
        select(func.count()).select_from(Order).where(Order.status == OrderStatus.FAILED)
    ) or 0

    completion_rate = (completed_orders / total_orders * 100) if total_orders > 0 else 0.0

    avg_rating_result = await db.scalar(
        select(func.avg(Review.rating))
    )
    average_order_rating = float(avg_rating_result) if avg_rating_result is not None else 0.0

    active_shifts = await db.scalar(
        select(func.count()).select_from(CourierShift).where(CourierShift.ended_at.is_(None))
    ) or 0

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    total_shifts_today = await db.scalar(
        select(func.count()).select_from(CourierShift).where(
            CourierShift.started_at >= today_start
        )
    ) or 0

    return AdminStatistics(
        total_users=total_users,
        total_clients=total_clients,
        total_couriers=total_couriers,
        active_couriers=active_couriers,
        verified_couriers=verified_couriers,
        total_orders=total_orders,
        pending_orders=pending_orders,
        in_progress_orders=in_progress_orders,
        completed_orders=completed_orders,
        cancelled_orders=cancelled_orders,
        failed_orders=failed_orders,
        completion_rate=round(completion_rate, 2),
        average_order_rating=round(average_order_rating, 2),
        active_shifts=active_shifts,
        total_shifts_today=total_shifts_today,
    )

@router.get("/couriers", response_model=CourierStatisticsList)
async def get_couriers_statistics(
    page: int = Query(1, ge=1, description="Номер страницы"),
    size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    status: Optional[CourierStatus] = Query(None, description="Фильтр по статусу курьера"),
    is_verified: Optional[bool] = Query(None, description="Фильтр по верификации"),
    is_active: Optional[bool] = Query(None, description="Фильтр по активности"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):

    base_query = select(User).where(User.role == UserRole.COURIER)

    if status is not None:
        base_query = base_query.where(User.courier_status == status)
    if is_verified is not None:
        base_query = base_query.where(User.is_verified == is_verified)
    if is_active is not None:
        base_query = base_query.where(User.is_active == is_active)

    count_query = select(func.count()).select_from(base_query.subquery())
    total = await db.scalar(count_query) or 0

    offset = (page - 1) * size
    query = base_query.offset(offset).limit(size).order_by(User.rating.desc())
    result = await db.execute(query)
    couriers = result.scalars().all()

    courier_stats = []
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    for courier in couriers:
        active_shift_stmt = select(CourierShift).where(
            and_(
                CourierShift.courier_id == courier.id,
                CourierShift.ended_at.is_(None)
            )
        )
        active_shift_result = await db.execute(active_shift_stmt)
        active_shift = active_shift_result.scalar_one_or_none()

        shifts_this_month = await db.scalar(
            select(func.count()).select_from(CourierShift).where(
                and_(
                    CourierShift.courier_id == courier.id,
                    CourierShift.started_at >= month_start
                )
            )
        ) or 0

        total_hours_result = await db.scalar(
            select(
                func.sum(
                    extract('epoch', CourierShift.ended_at - CourierShift.started_at) / 3600
                )
            ).where(
                and_(
                    CourierShift.courier_id == courier.id,
                    CourierShift.started_at >= month_start,
                    CourierShift.ended_at.isnot(None)
                )
            )
        )
        total_hours_this_month = float(total_hours_result) if total_hours_result is not None else 0.0

        orders_this_month = await db.scalar(
            select(func.count()).select_from(Order).where(
                and_(
                    Order.courier_id == courier.id,
                    Order.status == OrderStatus.COMPLETED,
                    Order.completed_at.isnot(None),
                    Order.completed_at >= month_start
                )
            )
        ) or 0

        courier_stats.append(
            CourierStatistics(
                id=courier.id,
                first_name=courier.first_name,
                last_name=courier.last_name,
                phone=courier.phone,
                email=courier.email,
                courier_status=courier.courier_status,
                is_verified=courier.is_verified,
                is_active=courier.is_active,
                rating=round(courier.rating, 2),
                total_orders=courier.total_orders,
                completed_orders=courier.completed_orders,
                active_shift_id=active_shift.id if active_shift else None,
                shifts_this_month=shifts_this_month,
                total_hours_this_month=round(total_hours_this_month, 2),
                orders_this_month=orders_this_month,
            )
        )

    pages = (total + size - 1) // size if total > 0 else 0

    return CourierStatisticsList(
        items=courier_stats,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )

@router.get("/clients", response_model=ClientStatisticsList)
async def get_all_clients(
    page: int = Query(1, ge=1, description="Номер страницы"),
    size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    is_active: Optional[bool] = Query(None, description="Фильтр по активности"),
    search: Optional[str] = Query(None, description="Поиск по имени, телефону или email"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):

    stmt = select(User).where(User.role == UserRole.CLIENT)

    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)

    if search:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                User.first_name.ilike(search_pattern),
                User.last_name.ilike(search_pattern),
                User.phone.ilike(search_pattern),
                User.email.ilike(search_pattern),
            )
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt) or 0

    stmt = stmt.offset((page - 1) * size).limit(size)

    result = await db.execute(stmt)
    clients = result.scalars().all()

    client_stats = []
    for client in clients:
        total_orders_stmt = select(func.count(Order.id)).where(Order.client_id == client.id)
        total_orders = await db.scalar(total_orders_stmt) or 0

        completed_orders_stmt = select(func.count(Order.id)).where(
            Order.client_id == client.id,
            Order.status == OrderStatus.COMPLETED
        )
        completed_orders = await db.scalar(completed_orders_stmt) or 0

        cancelled_orders_stmt = select(func.count(Order.id)).where(
            Order.client_id == client.id,
            Order.status == OrderStatus.CANCELLED
        )
        cancelled_orders = await db.scalar(cancelled_orders_stmt) or 0

        total_spent_stmt = select(func.sum(Order.final_price)).where(
            Order.client_id == client.id,
            Order.status == OrderStatus.COMPLETED
        )
        total_spent = await db.scalar(total_spent_stmt) or 0.0

        average_order_value = (total_spent / completed_orders) if completed_orders > 0 else 0.0

        last_order_stmt = select(Order.created_at).where(
            Order.client_id == client.id
        ).order_by(Order.created_at.desc()).limit(1)
        last_order_date = await db.scalar(last_order_stmt)

        client_stats.append(
            ClientStatistics(
                id=client.id,
                first_name=client.first_name,
                last_name=client.last_name,
                phone=client.phone,
                email=client.email,
                telegram_username=client.telegram_username,
                total_orders=total_orders,
                completed_orders=completed_orders,
                cancelled_orders=cancelled_orders,
                total_spent=round(total_spent, 2),
                average_order_value=round(average_order_value, 2),
                last_order_date=last_order_date,
                subscription_tier=None,
                is_active=client.is_active,
                created_at=client.created_at,
            )
        )

    pages = (total + size - 1) // size if total > 0 else 0

    return ClientStatisticsList(
        items=client_stats,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )

@router.get("/clients/{client_id}", response_model=ClientStatistics)
async def get_client_by_id(
    client_id: UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):

    stmt = select(User).where(User.id == client_id, User.role == UserRole.CLIENT)
    result = await db.execute(stmt)
    client = result.scalar_one_or_none()

    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Клиент не найден",
        )

    total_orders_stmt = select(func.count(Order.id)).where(Order.client_id == client.id)
    total_orders = await db.scalar(total_orders_stmt) or 0

    completed_orders_stmt = select(func.count(Order.id)).where(
        Order.client_id == client.id,
        Order.status == OrderStatus.COMPLETED
    )
    completed_orders = await db.scalar(completed_orders_stmt) or 0

    cancelled_orders_stmt = select(func.count(Order.id)).where(
        Order.client_id == client.id,
        Order.status == OrderStatus.CANCELLED
    )
    cancelled_orders = await db.scalar(cancelled_orders_stmt) or 0

    total_spent_stmt = select(func.sum(Order.final_price)).where(
        Order.client_id == client.id,
        Order.status == OrderStatus.COMPLETED
    )
    total_spent = await db.scalar(total_spent_stmt) or 0.0

    average_order_value = (total_spent / completed_orders) if completed_orders > 0 else 0.0

    last_order_stmt = select(Order.created_at).where(
        Order.client_id == client.id
    ).order_by(Order.created_at.desc()).limit(1)
    last_order_date = await db.scalar(last_order_stmt)

    return ClientStatistics(
        id=client.id,
        first_name=client.first_name,
        last_name=client.last_name,
        phone=client.phone,
        email=client.email,
        telegram_username=client.telegram_username,
        total_orders=total_orders,
        completed_orders=completed_orders,
        cancelled_orders=cancelled_orders,
        total_spent=round(total_spent, 2),
        average_order_value=round(average_order_value, 2),
        last_order_date=last_order_date,
        subscription_tier=None,
        is_active=client.is_active,
        created_at=client.created_at,
    )

@router.get("/couriers/{courier_id}", response_model=CourierStatistics)
async def get_courier_by_id(
    courier_id: UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):

    stmt = select(User).where(User.id == courier_id, User.role == UserRole.COURIER)
    result = await db.execute(stmt)
    courier = result.scalar_one_or_none()

    if courier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Курьер не найден",
        )

    active_shift_stmt = select(CourierShift).where(
        CourierShift.courier_id == courier.id,
        CourierShift.ended_at == None
    )
    active_shift_result = await db.execute(active_shift_stmt)
    active_shift = active_shift_result.scalar_one_or_none()

    from datetime import datetime
    now = datetime.now()
    current_month_start = datetime(now.year, now.month, 1)

    shifts_this_month_stmt = select(func.count(CourierShift.id)).where(
        CourierShift.courier_id == courier.id,
        CourierShift.started_at >= current_month_start
    )
    shifts_this_month = await db.scalar(shifts_this_month_stmt) or 0

    total_hours_stmt = select(func.sum(
        func.extract('epoch', CourierShift.ended_at - CourierShift.started_at) / 3600
    )).where(
        CourierShift.courier_id == courier.id,
        CourierShift.started_at >= current_month_start,
        CourierShift.ended_at != None
    )
    total_hours_this_month = float(await db.scalar(total_hours_stmt) or 0.0)

    orders_this_month_stmt = select(func.count(Order.id)).where(
        Order.courier_id == courier.id,
        Order.created_at >= current_month_start
    )
    orders_this_month = await db.scalar(orders_this_month_stmt) or 0

    return CourierStatistics(
        id=courier.id,
        first_name=courier.first_name,
        last_name=courier.last_name,
        phone=courier.phone,
        email=courier.email,
        courier_status=courier.courier_status,
        is_verified=courier.is_verified,
        is_active=courier.is_active,
        rating=round(courier.rating, 2),
        total_orders=courier.total_orders,
        completed_orders=courier.completed_orders,
        active_shift_id=active_shift.id if active_shift else None,
        shifts_this_month=shifts_this_month,
        total_hours_this_month=round(total_hours_this_month, 2),
        orders_this_month=orders_this_month,
    )

class ShiftOrderInfo(BaseModel):
    id: UUID
    status: str
    garbage_type: str
    number_of_bags: int
    final_price: float
    pickup_address: Optional[str] = None
    accepted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class ShiftDetail(BaseModel):
    id: UUID
    started_at: datetime
    ended_at: Optional[datetime] = None
    is_active: bool
    duration_minutes: Optional[int] = None
    orders_completed: int
    revenue: float
    orders: list[ShiftOrderInfo]

class ShiftsResponse(BaseModel):
    items: list[ShiftDetail]
    total: int
    page: int
    pages: int
    period_total_shifts: int
    period_total_hours: float
    period_total_orders: int
    period_total_revenue: float

@router.get("/couriers/{courier_id}/shifts", response_model=ShiftsResponse)
async def get_courier_shifts(
    courier_id: UUID,
    date_from: Optional[datetime] = Query(None, description="Начало периода"),
    date_to: Optional[datetime] = Query(None, description="Конец периода"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):

    courier_stmt = select(User).where(User.id == courier_id, User.role == UserRole.COURIER)
    courier = (await db.execute(courier_stmt)).scalar_one_or_none()
    if courier is None:
        raise HTTPException(status_code=404, detail="Курьер не найден")

    filters = [CourierShift.courier_id == courier_id]
    if date_from:
        if date_from.tzinfo is None:
            date_from = date_from.replace(tzinfo=timezone.utc)
        filters.append(CourierShift.started_at >= date_from)
    if date_to:
        if date_to.tzinfo is None:
            date_to = date_to.replace(tzinfo=timezone.utc)
        filters.append(CourierShift.started_at <= date_to)

    total = await db.scalar(
        select(func.count()).select_from(CourierShift).where(and_(*filters))
    ) or 0

    shifts_result = await db.execute(
        select(CourierShift)
        .where(and_(*filters))
        .order_by(CourierShift.started_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    shifts = shifts_result.scalars().all()

    period_hours_result = await db.scalar(
        select(func.sum(
            func.extract('epoch', CourierShift.ended_at - CourierShift.started_at) / 3600
        )).where(and_(*filters, CourierShift.ended_at.isnot(None)))
    )
    period_total_hours = float(period_hours_result or 0.0)

    items = []
    period_total_orders = 0
    period_total_revenue = 0.0

    for shift in shifts:
        order_filters = [
            Order.courier_id == courier_id,
            Order.accepted_at >= shift.started_at,
        ]
        if shift.ended_at:
            order_filters.append(Order.accepted_at <= shift.ended_at)

        orders_result = await db.execute(
            select(Order, Address)
            .outerjoin(Address, Order.pickup_address_id == Address.id)
            .where(and_(*order_filters))
            .order_by(Order.accepted_at)
        )
        rows = orders_result.all()

        shift_orders = []
        shift_revenue = 0.0
        for order, address in rows:
            status_val = order.status.value if hasattr(order.status, 'value') else str(order.status)
            garbage_val = order.garbage_type.value if hasattr(order.garbage_type, 'value') else str(order.garbage_type)
            if status_val == OrderStatus.COMPLETED.value:
                shift_revenue += float(order.final_price)
            shift_orders.append(ShiftOrderInfo(
                id=order.id,
                status=status_val,
                garbage_type=garbage_val,
                number_of_bags=order.number_of_bags,
                final_price=float(order.final_price),
                pickup_address=address.full_address if address else None,
                accepted_at=order.accepted_at,
                completed_at=order.completed_at,
            ))

        period_total_orders += len([o for o in shift_orders if o.status == OrderStatus.COMPLETED.value])
        period_total_revenue += shift_revenue

        duration_minutes = None
        end = shift.ended_at or datetime.now(timezone.utc)
        started = shift.started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        duration_minutes = int((end - started).total_seconds() / 60)

        items.append(ShiftDetail(
            id=shift.id,
            started_at=shift.started_at,
            ended_at=shift.ended_at,
            is_active=shift.ended_at is None,
            duration_minutes=duration_minutes,
            orders_completed=len([o for o in shift_orders if o.status == OrderStatus.COMPLETED.value]),
            revenue=round(shift_revenue, 2),
            orders=shift_orders,
        ))

    return ShiftsResponse(
        items=items,
        total=total,
        page=page,
        pages=(total + size - 1) // size if total > 0 else 0,
        period_total_shifts=total,
        period_total_hours=round(period_total_hours, 1),
        period_total_orders=period_total_orders,
        period_total_revenue=round(period_total_revenue, 2),
    )

@router.patch("/couriers/{courier_id}/verify")
async def verify_courier(
    courier_id: UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):

    stmt = select(User).where(User.id == courier_id, User.role == UserRole.COURIER)
    result = await db.execute(stmt)
    courier = result.scalar_one_or_none()

    if courier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Курьер не найден",
        )

    courier.is_verified = True
    await db.commit()

    return {"message": "Курьер успешно верифицирован"}

@router.patch("/couriers/{courier_id}/block")
async def block_courier(
    courier_id: UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):

    stmt = select(User).where(User.id == courier_id, User.role == UserRole.COURIER)
    result = await db.execute(stmt)
    courier = result.scalar_one_or_none()

    if courier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Курьер не найден",
        )

    courier.is_active = False
    await db.flush()
    await revoke_user_sessions(db, courier.id)
    await db.commit()

    return {"message": "Курьер успешно заблокирован"}

@router.patch("/couriers/{courier_id}/unblock")
async def unblock_courier(
    courier_id: UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):

    stmt = select(User).where(User.id == courier_id, User.role == UserRole.COURIER)
    result = await db.execute(stmt)
    courier = result.scalar_one_or_none()

    if courier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Курьер не найден",
        )

    courier.is_active = True
    await db.commit()

    return {"message": "Курьер успешно разблокирован"}

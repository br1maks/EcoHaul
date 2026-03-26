
from typing import Optional
from datetime import datetime, timezone, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.api.dependencies import require_admin
from app.models.user import User
from app.models.order import Order
from app.models.payment import Payment
from app.models.subscription import Subscription
from app.models.review import Review
from app.models.courier_shift import CourierShift
from app.models.enums import (
    OrderStatus,
    PaymentStatus,
    UserRole,
    SubscriptionTier
)

router = APIRouter(prefix="/admin/statistics", tags=["Админ: Статистика"])

class OverviewStatistics(BaseModel):

    total_users: int = Field(..., description="Всего пользователей")
    total_clients: int = Field(..., description="Всего клиентов")
    total_couriers: int = Field(..., description="Всего курьеров")
    verified_couriers: int = Field(..., description="Верифицированных курьеров")
    active_couriers: int = Field(..., description="Активных курьеров (в смене)")

    total_orders: int = Field(..., description="Всего заказов")
    pending_orders: int = Field(..., description="Ожидающих заказов")
    in_progress_orders: int = Field(..., description="Заказов в процессе")
    completed_orders: int = Field(..., description="Завершённых заказов")
    cancelled_orders: int = Field(..., description="Отменённых заказов")

    total_revenue: float = Field(..., description="Общий доход (BYN)")
    revenue_today: float = Field(..., description="Доход сегодня (BYN)")
    revenue_this_month: float = Field(..., description="Доход за месяц (BYN)")
    avg_order_price: float = Field(..., description="Средняя цена заказа (BYN)")

    active_subscriptions: int = Field(..., description="Активных подписок")
    basic_subscriptions: int = Field(..., description="BASIC подписок")
    premium_subscriptions: int = Field(..., description="PREMIUM подписок")

    total_reviews: int = Field(..., description="Всего отзывов")
    avg_rating: float = Field(..., description="Средний рейтинг курьеров")

class PeriodStatistics(BaseModel):
    period_start: datetime
    period_end: datetime

    orders_count: int = Field(..., description="Заказов за период")
    completed_orders_count: int = Field(..., description="Завершённых заказов")
    cancelled_orders_count: int = Field(..., description="Отменённых заказов")

    revenue: float = Field(..., description="Доход за период (BYN)")
    avg_order_price: float = Field(..., description="Средняя цена заказа (BYN)")

    new_clients: int = Field(..., description="Новых клиентов")
    new_couriers: int = Field(..., description="Новых курьеров")

class TopCourier(BaseModel):
    courier_id: UUID
    courier_name: str
    rating: float
    completed_orders: int
    total_revenue: float
    avg_order_price: float

@router.get("/overview", response_model=OverviewStatistics)
async def get_overview_statistics(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    users_stmt = select(
        func.count().label("total"),
        func.sum(case((User.role == UserRole.CLIENT, 1), else_=0)).label("clients"),
        func.sum(case((User.role == UserRole.COURIER, 1), else_=0)).label("couriers"),
        func.sum(case((and_(User.role == UserRole.COURIER, User.is_verified == True), 1), else_=0)).label("verified_couriers"),
    ).select_from(User)

    users_result = await db.execute(users_stmt)
    users_data = users_result.one()

    active_couriers_stmt = select(func.count(func.distinct(CourierShift.courier_id))).where(
        CourierShift.ended_at == None
    )
    active_couriers_result = await db.execute(active_couriers_stmt)
    active_couriers = active_couriers_result.scalar() or 0

    orders_stmt = select(
        func.count().label("total"),
        func.sum(case((Order.status == OrderStatus.PENDING, 1), else_=0)).label("pending"),
        func.sum(case((Order.status == OrderStatus.IN_PROGRESS, 1), else_=0)).label("in_progress"),
        func.sum(case((Order.status == OrderStatus.COMPLETED, 1), else_=0)).label("completed"),
        func.sum(case((Order.status == OrderStatus.CANCELLED, 1), else_=0)).label("cancelled"),
    ).select_from(Order)

    orders_result = await db.execute(orders_stmt)
    orders_data = orders_result.one()

    total_revenue_stmt = select(func.sum(Order.final_price)).where(
        Order.status == OrderStatus.COMPLETED
    )
    total_revenue_result = await db.execute(total_revenue_stmt)
    total_revenue = total_revenue_result.scalar() or 0.0

    revenue_today_stmt = select(func.sum(Order.final_price)).where(
        Order.status == OrderStatus.COMPLETED,
        Order.completed_at >= today_start
    )
    revenue_today_result = await db.execute(revenue_today_stmt)
    revenue_today = revenue_today_result.scalar() or 0.0

    revenue_month_stmt = select(func.sum(Order.final_price)).where(
        Order.status == OrderStatus.COMPLETED,
        Order.completed_at >= month_start
    )
    revenue_month_result = await db.execute(revenue_month_stmt)
    revenue_month = revenue_month_result.scalar() or 0.0

    avg_price_stmt = select(func.avg(Order.final_price)).where(
        Order.status == OrderStatus.COMPLETED
    )
    avg_price_result = await db.execute(avg_price_stmt)
    avg_order_price = avg_price_result.scalar() or 0.0

    subscriptions_stmt = select(
        func.count().label("total"),
        func.sum(case((Subscription.tier == SubscriptionTier.BASIC, 1), else_=0)).label("basic"),
        func.sum(case((Subscription.tier == SubscriptionTier.PREMIUM, 1), else_=0)).label("premium"),
    ).select_from(Subscription).where(
        Subscription.is_active == True,
        Subscription.end_date > now
    )

    subscriptions_result = await db.execute(subscriptions_stmt)
    subscriptions_data = subscriptions_result.one()

    reviews_stmt = select(
        func.count().label("total"),
        func.avg(Review.rating).label("avg_rating")
    ).select_from(Review).where(
        Review.is_visible == True
    )

    reviews_result = await db.execute(reviews_stmt)
    reviews_data = reviews_result.one()

    return OverviewStatistics(
        total_users=users_data.total or 0,
        total_clients=users_data.clients or 0,
        total_couriers=users_data.couriers or 0,
        verified_couriers=users_data.verified_couriers or 0,
        active_couriers=active_couriers,

        total_orders=orders_data.total or 0,
        pending_orders=orders_data.pending or 0,
        in_progress_orders=orders_data.in_progress or 0,
        completed_orders=orders_data.completed or 0,
        cancelled_orders=orders_data.cancelled or 0,

        total_revenue=round(total_revenue, 2),
        revenue_today=round(revenue_today, 2),
        revenue_this_month=round(revenue_month, 2),
        avg_order_price=round(avg_order_price, 2),

        active_subscriptions=subscriptions_data.total or 0,
        basic_subscriptions=subscriptions_data.basic or 0,
        premium_subscriptions=subscriptions_data.premium or 0,

        total_reviews=reviews_data.total or 0,
        avg_rating=round(reviews_data.avg_rating or 0.0, 2),
    )

@router.get("/period", response_model=PeriodStatistics)
async def get_period_statistics(
    start_date: datetime = Query(..., description="Начало периода (ISO format)"),
    end_date: datetime = Query(..., description="Конец периода (ISO format)"),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    
    orders_stmt = select(
        func.count().label("total"),
        func.sum(case((Order.status == OrderStatus.COMPLETED, 1), else_=0)).label("completed"),
        func.sum(case((Order.status == OrderStatus.CANCELLED, 1), else_=0)).label("cancelled"),
    ).select_from(Order).where(
        Order.created_at >= start_date,
        Order.created_at <= end_date
    )

    orders_result = await db.execute(orders_stmt)
    orders_data = orders_result.one()

    revenue_stmt = select(
        func.sum(Order.final_price).label("revenue"),
        func.avg(Order.final_price).label("avg_price")
    ).where(
        Order.status == OrderStatus.COMPLETED,
        Order.completed_at >= start_date,
        Order.completed_at <= end_date
    )

    revenue_result = await db.execute(revenue_stmt)
    revenue_data = revenue_result.one()

    new_clients_stmt = select(func.count()).select_from(User).where(
        User.role == UserRole.CLIENT,
        User.created_at >= start_date,
        User.created_at <= end_date
    )
    new_clients_result = await db.execute(new_clients_stmt)
    new_clients = new_clients_result.scalar() or 0

    new_couriers_stmt = select(func.count()).select_from(User).where(
        User.role == UserRole.COURIER,
        User.created_at >= start_date,
        User.created_at <= end_date
    )
    new_couriers_result = await db.execute(new_couriers_stmt)
    new_couriers = new_couriers_result.scalar() or 0

    return PeriodStatistics(
        period_start=start_date,
        period_end=end_date,
        orders_count=orders_data.total or 0,
        completed_orders_count=orders_data.completed or 0,
        cancelled_orders_count=orders_data.cancelled or 0,
        revenue=round(revenue_data.revenue or 0.0, 2),
        avg_order_price=round(revenue_data.avg_price or 0.0, 2),
        new_clients=new_clients,
        new_couriers=new_couriers,
    )

@router.get("/top-couriers", response_model=list[TopCourier])
async def get_top_couriers(
    limit: int = Query(10, ge=1, le=100, description="Количество курьеров в топе"),
    order_by: str = Query("rating", description="Сортировка: rating, orders, revenue"),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    subquery = (
        select(
            Order.courier_id,
            func.count(Order.id).label("completed_orders"),
            func.sum(Order.final_price).label("total_revenue"),
            func.avg(Order.final_price).label("avg_order_price"),
        )
        .where(Order.status == OrderStatus.COMPLETED)
        .group_by(Order.courier_id)
        .subquery()
    )

    stmt = (
        select(
            User.id.label("courier_id"),
            (User.first_name + " " + User.last_name).label("courier_name"),
            User.rating,
            func.coalesce(subquery.c.completed_orders, 0).label("completed_orders"),
            func.coalesce(subquery.c.total_revenue, 0.0).label("total_revenue"),
            func.coalesce(subquery.c.avg_order_price, 0.0).label("avg_order_price"),
        )
        .select_from(User)
        .outerjoin(subquery, User.id == subquery.c.courier_id)
        .where(User.role == UserRole.COURIER)
    )

    if order_by == "orders":
        stmt = stmt.order_by(subquery.c.completed_orders.desc().nullslast())
    elif order_by == "revenue":
        stmt = stmt.order_by(subquery.c.total_revenue.desc().nullslast())
    else:
        stmt = stmt.order_by(User.rating.desc())

    stmt = stmt.limit(limit)

    result = await db.execute(stmt)
    couriers = result.all()

    return [
        TopCourier(
            courier_id=courier.courier_id,
            courier_name=courier.courier_name,
            rating=round(courier.rating or 0.0, 2),
            completed_orders=courier.completed_orders or 0,
            total_revenue=round(courier.total_revenue or 0.0, 2),
            avg_order_price=round(courier.avg_order_price or 0.0, 2),
        )
        for courier in couriers
    ]

class TopClient(BaseModel):
    client_id: UUID
    client_name: str
    total_orders: int
    total_spent: float

class MonthlyStats(BaseModel):
    month: str = Field(..., description="Месяц (например, 'Июль 2024')")
    orders: int = Field(..., description="Количество заказов")
    revenue: float = Field(..., description="Доход (BYN)")

class GarbageTypeStats(BaseModel):
    garbage_type: str = Field(..., description="Тип мусора (enum значение)")
    garbage_type_label: str = Field(..., description="Тип мусора (текстовая метка)")
    count: int = Field(..., description="Количество заказов")
    revenue: float = Field(..., description="Доход (BYN)")
    percentage: float = Field(..., description="Процент от общего количества")

class AnalyticsData(BaseModel):

    total_revenue: float
    revenue_change: float
    total_orders: int
    orders_change: float
    total_clients: int
    clients_change: float
    total_couriers: int
    couriers_change: float
    avg_order_value: float
    avg_order_value_change: float
    completion_rate: float
    completion_rate_change: float

    orders_by_month: list[MonthlyStats]

    garbage_type_stats: list[GarbageTypeStats]

    top_couriers: list[TopCourier]
    top_clients: list[TopClient]

@router.get("/top-clients", response_model=list[TopClient])
async def get_top_clients(
    limit: int = Query(10, ge=1, le=100, description="Количество клиентов в топе"),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):

    stmt = (
        select(
            User.id.label("client_id"),
            (User.first_name + " " + User.last_name).label("client_name"),
            func.count(Order.id).label("total_orders"),
            func.sum(Order.final_price).label("total_spent"),
        )
        .select_from(User)
        .join(Order, User.id == Order.client_id)
        .where(
            User.role == UserRole.CLIENT,
            Order.status == OrderStatus.COMPLETED
        )
        .group_by(User.id, User.first_name, User.last_name)
        .order_by(func.sum(Order.final_price).desc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    clients = result.all()

    return [
        TopClient(
            client_id=client.client_id,
            client_name=client.client_name,
            total_orders=client.total_orders or 0,
            total_spent=round(client.total_spent or 0.0, 2),
        )
        for client in clients
    ]

@router.get("/monthly", response_model=list[MonthlyStats])
async def get_monthly_statistics(
    months: int = Query(6, ge=1, le=24, description="Количество месяцев для отображения"),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):

    now = datetime.now(timezone.utc)
    month_names_ru = {
        1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
        5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
        9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
    }

    results = []

    for i in range(months - 1, -1, -1):
        month_date = now - timedelta(days=30 * i)
        month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1, day=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1, day=1)

        stmt = select(
            func.count(Order.id).label("orders"),
            func.coalesce(func.sum(
                case((Order.status == OrderStatus.COMPLETED, Order.final_price), else_=0)
            ), 0).label("revenue")
        ).where(
            Order.created_at >= month_start,
            Order.created_at < month_end
        )

        result = await db.execute(stmt)
        data = result.one()

        month_name = month_names_ru[month_start.month]

        results.append(
            MonthlyStats(
                month=month_name,
                orders=data.orders or 0,
                revenue=round(data.revenue or 0.0, 2)
            )
        )

    return results

@router.get("/garbage-types", response_model=list[GarbageTypeStats])
async def get_garbage_type_statistics(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):

    total_stmt = select(func.count(Order.id)).where(
        Order.status == OrderStatus.COMPLETED
    )
    total_result = await db.execute(total_stmt)
    total_orders = total_result.scalar() or 1

    stmt = (
        select(
            Order.garbage_type,
            func.count(Order.id).label("count"),
            func.sum(Order.final_price).label("revenue")
        )
        .where(Order.status == OrderStatus.COMPLETED)
        .group_by(Order.garbage_type)
        .order_by(func.count(Order.id).desc())
    )

    result = await db.execute(stmt)
    types_data = result.all()

    type_labels = {
        "HOUSEHOLD": "Бытовой мусор",
        "CONSTRUCTION": "Строительный мусор",
    }

    results = []
    for row in types_data:
        gt = row.garbage_type
        garbage_type_value = gt.value if hasattr(gt, 'value') else str(gt)
        row_count = getattr(row, 'count', 0)
        row_revenue = getattr(row, 'revenue', 0.0)
        count = int(row_count) if row_count is not None else 0
        revenue = float(row_revenue) if row_revenue is not None else 0.0
        percentage = float(round((count / total_orders) * 100, 1)) if total_orders > 0 else 0.0
        results.append(
            GarbageTypeStats(
                garbage_type=garbage_type_value,
                garbage_type_label=type_labels.get(garbage_type_value, garbage_type_value),
                count=count,
                revenue=round(revenue, 2),
                percentage=percentage
            )
        )
    return results

@router.get("/analytics", response_model=AnalyticsData)
async def get_analytics_data(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if month_start.month == 1:
        prev_month_start = month_start.replace(year=month_start.year - 1, month=12)
    else:
        prev_month_start = month_start.replace(month=month_start.month - 1)

    current_revenue_stmt = select(func.sum(Order.final_price)).where(
        Order.status == OrderStatus.COMPLETED,
        Order.completed_at >= month_start
    )
    current_revenue = (await db.execute(current_revenue_stmt)).scalar() or 0.0

    current_orders_stmt = select(func.count(Order.id)).where(
        Order.created_at >= month_start
    )
    current_orders = (await db.execute(current_orders_stmt)).scalar() or 0

    current_clients_stmt = select(func.count(User.id)).where(
        User.role == UserRole.CLIENT,
        User.created_at >= month_start
    )
    current_clients = (await db.execute(current_clients_stmt)).scalar() or 0

    current_couriers_stmt = select(func.count(User.id)).where(
        User.role == UserRole.COURIER,
        User.created_at >= month_start
    )
    current_couriers = (await db.execute(current_couriers_stmt)).scalar() or 0

    current_avg_stmt = select(func.avg(Order.final_price)).where(
        Order.status == OrderStatus.COMPLETED,
        Order.completed_at >= month_start
    )
    current_avg = (await db.execute(current_avg_stmt)).scalar() or 0.0

    current_completion_stmt = select(
        func.count(Order.id).label("total"),
        func.sum(case((Order.status == OrderStatus.COMPLETED, 1), else_=0)).label("completed")
    ).where(Order.created_at >= month_start)
    current_completion_data = (await db.execute(current_completion_stmt)).one()
    current_completion_rate = (
        (current_completion_data.completed / current_completion_data.total * 100)
        if current_completion_data.total > 0 else 0.0
    )

    prev_revenue_stmt = select(func.sum(Order.final_price)).where(
        Order.status == OrderStatus.COMPLETED,
        Order.completed_at >= prev_month_start,
        Order.completed_at < month_start
    )
    prev_revenue = (await db.execute(prev_revenue_stmt)).scalar() or 0.0

    prev_orders_stmt = select(func.count(Order.id)).where(
        Order.created_at >= prev_month_start,
        Order.created_at < month_start
    )
    prev_orders = (await db.execute(prev_orders_stmt)).scalar() or 1

    prev_clients_stmt = select(func.count(User.id)).where(
        User.role == UserRole.CLIENT,
        User.created_at >= prev_month_start,
        User.created_at < month_start
    )
    prev_clients = (await db.execute(prev_clients_stmt)).scalar() or 1

    prev_couriers_stmt = select(func.count(User.id)).where(
        User.role == UserRole.COURIER,
        User.created_at >= prev_month_start,
        User.created_at < month_start
    )
    prev_couriers = (await db.execute(prev_couriers_stmt)).scalar() or 1

    prev_avg_stmt = select(func.avg(Order.final_price)).where(
        Order.status == OrderStatus.COMPLETED,
        Order.completed_at >= prev_month_start,
        Order.completed_at < month_start
    )
    prev_avg = (await db.execute(prev_avg_stmt)).scalar() or 1.0

    prev_completion_stmt = select(
        func.count(Order.id).label("total"),
        func.sum(case((Order.status == OrderStatus.COMPLETED, 1), else_=0)).label("completed")
    ).where(
        Order.created_at >= prev_month_start,
        Order.created_at < month_start
    )
    prev_completion_data = (await db.execute(prev_completion_stmt)).one()
    prev_completion_rate = (
        (prev_completion_data.completed / prev_completion_data.total * 100)
        if prev_completion_data.total > 0 else 1.0
    )

    def calculate_change(current: float, previous: float) -> float:
        current = float(current) if current is not None else 0.0
        previous = float(previous) if previous is not None else 0.0

        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round(((current - previous) / previous) * 100, 1)

    top_couriers = await get_top_couriers(limit=5, order_by="revenue", db=db)

    top_clients = await get_top_clients(limit=5, db=db)

    orders_by_month = await get_monthly_statistics(months=6, db=db)

    garbage_types = await get_garbage_type_statistics(db=db)

    total_revenue_stmt = select(func.sum(Order.final_price)).where(
        Order.status == OrderStatus.COMPLETED
    )
    total_revenue = (await db.execute(total_revenue_stmt)).scalar() or 0.0

    total_orders_stmt = select(func.count(Order.id))
    total_orders = (await db.execute(total_orders_stmt)).scalar() or 0

    total_clients_stmt = select(func.count(User.id)).where(User.role == UserRole.CLIENT)
    total_clients = (await db.execute(total_clients_stmt)).scalar() or 0

    total_couriers_stmt = select(func.count(User.id)).where(User.role == UserRole.COURIER)
    total_couriers = (await db.execute(total_couriers_stmt)).scalar() or 0

    total_avg_stmt = select(func.avg(Order.final_price)).where(
        Order.status == OrderStatus.COMPLETED
    )
    total_avg = (await db.execute(total_avg_stmt)).scalar() or 0.0

    total_completion_stmt = select(
        func.count(Order.id).label("total"),
        func.sum(case((Order.status == OrderStatus.COMPLETED, 1), else_=0)).label("completed")
    )
    total_completion_data = (await db.execute(total_completion_stmt)).one()
    total_completion_rate = (
        (total_completion_data.completed / total_completion_data.total * 100)
        if total_completion_data.total > 0 else 0.0
    )

    return AnalyticsData(
        total_revenue=round(total_revenue, 2),
        revenue_change=calculate_change(current_revenue, prev_revenue),
        total_orders=total_orders,
        orders_change=calculate_change(current_orders, prev_orders),
        total_clients=total_clients,
        clients_change=calculate_change(current_clients, prev_clients),
        total_couriers=total_couriers,
        couriers_change=calculate_change(current_couriers, prev_couriers),
        avg_order_value=round(total_avg, 2),
        avg_order_value_change=calculate_change(current_avg, prev_avg),
        completion_rate=round(total_completion_rate, 1),
        completion_rate_change=calculate_change(current_completion_rate, prev_completion_rate),

        orders_by_month=orders_by_month,
        garbage_type_stats=garbage_types,
        top_couriers=top_couriers,
        top_clients=top_clients,
    )

from typing import Optional
from uuid import UUID
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.security import verify_password
from app.api.dependencies import get_current_active_user, require_courier, require_admin, require_order_operator
from app.models.user import User
from app.models.enums import UserRole
from app.models.order import Order
from app.models.address import Address
from app.models.notification import Notification
from app.models.order_queue import OrderQueue
from app.models.enums import OrderStatus, GarbageType, SubscriptionTier, NotificationType, NotificationChannel, OrderQueueStatus
from app.models.subscription import Subscription
from app.websocket import manager, create_notification_message
from app.tasks.notifications import notify_order_created, notify_order_accepted, notify_order_completed, notify_new_order_to_couriers
from app.core.redis import get_redis
import json 

class OrderCreate(BaseModel):
    pickup_address_id: UUID
    garbage_type: GarbageType = GarbageType.HOUSEHOLD
    number_of_bags: int = Field(..., ge=1, le=50)
    description: Optional[str] = Field(None, max_length=1000)
    scheduled_time: datetime

    @field_validator('scheduled_time')
    @classmethod
    def validate_scheduled_time(cls, v: datetime) -> datetime:
        now = datetime.now(timezone.utc)
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v < now + timedelta(minutes=15):
            raise ValueError('Время вывоза должно быть не раньше чем через 15 минут')
        hour = v.astimezone(timezone(timedelta(hours=3))).hour
        if hour < 8 or hour >= 21:
            raise ValueError('Вывоз доступен только с 08:00 до 21:00')
        return v

class AddressResponse(BaseModel):
    id: UUID
    full_address: str
    city: str
    district: str
    street: str
    house_number: str
    apartment: Optional[str] = None
    entrance: Optional[int] = None
    floor: Optional[int] = None
    notes: Optional[str] = None
    latitude: float
    longitude: float

    model_config = {"from_attributes": True}

class OrderResponse(BaseModel):
    id: UUID
    client_id: UUID
    courier_id: Optional[UUID] = None
    pickup_address_id: UUID
    pickup_address: Optional[AddressResponse] = None
    garbage_type: GarbageType
    number_of_bags: int
    description: Optional[str] = None
    status: OrderStatus
    price_before_discount: float
    discount_amount: float
    final_price: float
    subscription_tier_used: Optional[SubscriptionTier] = None
    scheduled_time: Optional[datetime] = None
    priority: int = 0
    expires_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    created_at: datetime
    is_expired: bool = Field(default=False, description="Истёк ли срок заказа")
    time_remaining_seconds: Optional[int] = Field(default=None, description="Оставшееся время в секундах")

    model_config = {"from_attributes": True}

class OrderListResponse(BaseModel):
    items: list[OrderResponse]
    total: int
    page: int
    size: int
    pages: int

class OrderStatusUpdate(BaseModel):
    status: OrderStatus

class OrderCancel(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)

class OrderAccept(BaseModel):
    password: str = Field(..., min_length=4, max_length=72, description="Пароль курьера для подтверждения взятия заказа")

GARBAGE_TYPE_LABELS = {
    "HOUSEHOLD": "Бытовой мусор",
    "CONSTRUCTION": "Строительный мусор",
}

router = APIRouter(prefix="/orders", tags=["Заказы"])

@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    data: OrderCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Address).where(
        Address.id == data.pickup_address_id,
        Address.user_id == current_user.id,
        Address.deleted_at.is_(None),
    )

    result = await db.execute(stmt)
    address = result.scalar_one_or_none()

    if address is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Адрес не найден",
        )

    now = datetime.now(timezone.utc)
    scheduled = data.scheduled_time
    if scheduled.tzinfo is None:
        scheduled = scheduled.replace(tzinfo=timezone.utc)
    if scheduled < now + timedelta(minutes=15):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Время вывоза должно быть не раньше чем через 15 минут от текущего времени",
        )
    minsk_hour = scheduled.astimezone(timezone(timedelta(hours=3))).hour
    if minsk_hour < 8 or minsk_hour >= 21:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Вывоз доступен только с 08:00 до 21:00",
        )

    price_before_discount = data.number_of_bags * settings.BASE_PRICE_PER_BAG

    discount_amount = 0.0
    subscription_tier_used = None

    stmt = select(Subscription).where(
        Subscription.user_id == current_user.id,
        Subscription.is_active == True,
        Subscription.end_date > now,
    )

    result = await db.execute(stmt)
    subscription = result.scalar_one_or_none()

    if subscription:
        subscription_tier_used = subscription.tier

        if subscription.tier == SubscriptionTier.BASIC:
            discount_amount = price_before_discount * settings.BASIC_SUBSCRIPTION_DISCOUNT
        elif subscription.tier == SubscriptionTier.PREMIUM:
            discount_amount = price_before_discount * settings.PREMIUM_SUBSCRIPTION_DISCOUNT

    final_price = price_before_discount - discount_amount

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)

    order = Order(
        client_id=current_user.id,
        pickup_address_id=data.pickup_address_id,
        garbage_type=data.garbage_type,
        number_of_bags=data.number_of_bags,
        description=data.description,
        status=OrderStatus.PENDING,
        price_before_discount=price_before_discount,
        discount_amount=discount_amount,
        final_price=final_price,
        subscription_tier_used=subscription_tier_used,
        scheduled_time=data.scheduled_time,
        priority=0,
        expires_at=expires_at,
    )
    db.add(order)
    await db.flush()
    await db.commit()
    await db.refresh(order)

    from app.websocket import manager
    from app.websocket.schemas import create_new_order_message
    from app.models.enums import UserRole

    couriers_stmt = select(User).where(
        User.role == UserRole.COURIER,
        User.is_verified == True,
        User.is_active == True
    )
    couriers_result = await db.execute(couriers_stmt)
    couriers = couriers_result.scalars().all()

    if couriers:
        courier_ids = [courier.id for courier in couriers]

        await db.refresh(order, ["pickup_address"])

        ws_message = create_new_order_message({
            "id": order.id,
            "pickup_address": order.pickup_address.full_address if order.pickup_address else "Адрес не указан",
            "delivery_address": None,
            "garbage_type": str(order.garbage_type),
            "number_of_bags": order.number_of_bags,
            "final_price": order.final_price,
            "created_at": order.created_at,
        })

        await manager.send_to_users(courier_ids, ws_message)

        courier_telegram_ids = [c.telegram_id for c in couriers if c.telegram_id]
        if courier_telegram_ids:
            pickup_address = order.pickup_address.full_address if order.pickup_address else "Адрес не указан"
            notify_new_order_to_couriers.delay(
                courier_telegram_ids,
                pickup_address,
                float(order.final_price),
                str(order.garbage_type),
                order.number_of_bags,
            )

        if current_user.telegram_id:
            notify_order_created.delay(current_user.telegram_id, str(order.id))

    await get_redis().delete("orders:available")
    await db.refresh(order, ["pickup_address"])
    return order

@router.get("", response_model=OrderListResponse)
async def get_my_orders(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):

    count_stmt = select(func.count()).select_from(Order).where(Order.client_id == current_user.id)
    total = await db.scalar(count_stmt) or 0 

    offset = (page - 1) * size
    stmt = select(Order).where(Order.client_id == current_user.id).options(selectinload(Order.pickup_address)).order_by(Order.created_at.desc()).offset(offset).limit(size)
    result = await db.execute(stmt)
    orders = result.scalars().all()

    pages = (total + size - 1) // size

    return OrderListResponse(
        items=orders,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )

@router.get("/available", response_model=list[OrderResponse])
async def get_available_orders(
    current_user: User = Depends(require_courier),
    db: AsyncSession = Depends(get_db),
):  
    redis = get_redis()
    cache_key = "orders:available"

    cached = await redis.get(cache_key)
    if cached:
        now = datetime.now(timezone.utc)
        return [item for item in json.loads(cached)
                if not item.get("expires_at") or datetime.fromisoformat(item["expires_at"]) > now]
    
    stmt = (
        select(Order)
        .where(Order.status == OrderStatus.PENDING,
               (Order.expires_at.is_(None)) | (Order.expires_at > datetime.now(timezone.utc)))
        .options(selectinload(Order.pickup_address))
        .order_by(Order.priority.desc(), Order.created_at.asc())
    )
    result = await db.execute(stmt)
    orders = result.scalars().all()

    serialized = [
        OrderResponse.model_validate(o).model_dump(mode="json")
        for o in orders
    ]
    await redis.setex(cache_key, 180, json.dumps(serialized))
    return orders

@router.get("/my-deliveries", response_model=OrderListResponse)
async def get_my_deliveries(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status_filter: Optional[OrderStatus] = Query(None, description="Фильтр по статусу заказа"),
    current_user: User = Depends(require_courier),
    db: AsyncSession = Depends(get_db),
):

    filters = [Order.courier_id == current_user.id]
    if status_filter:
        filters.append(Order.status == status_filter)

    count_stmt = select(func.count()).select_from(Order).where(and_(*filters))
    total = await db.scalar(count_stmt) or 0

    offset = (page - 1) * size
    stmt = (
        select(Order)
        .where(and_(*filters))
        .options(selectinload(Order.pickup_address))
        .order_by(Order.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    result = await db.execute(stmt)
    orders = result.scalars().all()

    pages = (total + size - 1) // size

    return OrderListResponse(
        items=orders,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )

@router.get("/all", response_model=OrderListResponse)
async def get_all_orders(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status_filter: Optional[OrderStatus] = Query(None, description="Фильтр по статусу заказа"),
    client_id: Optional[UUID] = Query(None, description="Фильтр по ID клиента"),
    courier_id: Optional[UUID] = Query(None, description="Фильтр по ID курьера"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    filters = []
    if status_filter:
        filters.append(Order.status == status_filter)
    if client_id:
        filters.append(Order.client_id == client_id)
    if courier_id:
        filters.append(Order.courier_id == courier_id)

    if filters:
        count_stmt = select(func.count()).select_from(Order).where(and_(*filters))
    else:
        count_stmt = select(func.count()).select_from(Order)

    total = await db.scalar(count_stmt) or 0

    offset = (page - 1) * size

    if filters:
        stmt = (
            select(Order)
            .where(and_(*filters))
            .options(selectinload(Order.pickup_address))
            .order_by(Order.created_at.desc())
            .offset(offset)
            .limit(size)
        )
    else:
        stmt = (
            select(Order)
            .options(selectinload(Order.pickup_address))
            .order_by(Order.created_at.desc())
            .offset(offset)
            .limit(size)
        )

    result = await db.execute(stmt)
    orders = result.scalars().all()

    pages = (total + size - 1) // size

    return OrderListResponse(
        items=orders,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )

class BulkAcceptOrders(BaseModel):
    order_ids: list[UUID] = Field(..., min_length=1, max_length=10, description="Список ID заказов для взятия (макс 10)")
    password: str = Field(..., min_length=4, max_length=72, description="Пароль курьера для подтверждения")

class BulkAcceptResponse(BaseModel):
    accepted_orders: list[OrderResponse] = Field(description="Успешно принятые заказы")
    failed_orders: list[dict] = Field(description="Заказы, которые не удалось принять")
    total_accepted: int
    total_failed: int

@router.post("/accept-bulk", response_model=BulkAcceptResponse)
async def accept_orders_bulk(
    data: BulkAcceptOrders,
    current_user: User = Depends(require_courier),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="У курьера не установлен пароль",
        )

    if not verify_password(data.password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный пароль",
        )

    accepted_orders = []
    failed_orders = []

    for order_id in data.order_ids:
        try:
            stmt = select(Order).where(Order.id == order_id).options(selectinload(Order.pickup_address)).with_for_update(of=Order)
            result = await db.execute(stmt)
            order = result.scalar_one_or_none()

            if order is None:
                failed_orders.append({
                    "order_id": str(order_id),
                    "reason": "Заказ не найден"
                })
                continue

            if order.status != OrderStatus.PENDING or order.is_expired:
                failed_orders.append({
                    "order_id": str(order_id),
                    "reason": f"Заказ уже в статусе {str(order.status)}"
                })
                continue

            now = datetime.now(timezone.utc)
            order.courier_id = current_user.id
            order.status = OrderStatus.ASSIGNED
            order.accepted_at = now

            queue_entry = OrderQueue(
                order_id=order.id,
                courier_id=current_user.id,
                status=OrderQueueStatus.ACCEPTED,
                priority=order.priority,
                distance_km=0.0,
                offered_at=now,
                expires_at=now + timedelta(minutes=30),
                responded_at=now,
            )
            db.add(queue_entry)

            addr = order.pickup_address
            addr_str = ""
            if addr:
                addr_str = f"\nАдрес: {addr.street}, {addr.house_number}"
                if addr.apartment:
                    addr_str += f", кв. {addr.apartment}"

            garbage_label = GARBAGE_TYPE_LABELS.get(str(order.garbage_type), str(order.garbage_type))
            notification_message = (
                f"{garbage_label} · {order.number_of_bags} мешк.\n"
                f"Цена: {order.final_price} руб.{addr_str}"
            )
            if order.description:
                notification_message += f"\n{order.description}"

            notification = Notification(
                user_id=current_user.id,
                order_id=order.id,
                notification_type=NotificationType.ORDER_ASSIGNED,
                channel=NotificationChannel.IN_APP,
                title="Заказ принят",
                message=notification_message,
                sent_at=datetime.now(timezone.utc),
            )
            db.add(notification)
            await db.flush()

            ws_message = create_notification_message({
                "id": notification.id,
                "title": notification.title,
                "message": notification.message,
                "priority": "HIGH",
                "created_at": notification.sent_at,
            })
            await manager.send_personal_message(current_user.id, ws_message)

            accepted_orders.append(order)

        except Exception as e:
            failed_orders.append({
                "order_id": str(order_id),
                "reason": f"Ошибка: {str(e)}"
            })

    await db.flush()

    await get_redis().delete("orders:available")
    return BulkAcceptResponse(
        accepted_orders=accepted_orders,
        failed_orders=failed_orders,
        total_accepted=len(accepted_orders),
        total_failed=len(failed_orders),
    )

@router.post("/{order_id}/accept", response_model=OrderResponse)
async def accept_order(
    order_id: UUID,
    data: Optional[OrderAccept] = None,
    current_user: User = Depends(require_courier),
    db: AsyncSession = Depends(get_db),
):
    if data and data.password:
        if not current_user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="У курьера не установлен пароль",
            )

        if not verify_password(data.password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный пароль",
            )

    stmt = select(Order).where(Order.id == order_id).options(selectinload(Order.pickup_address)).with_for_update(of=Order)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заказ с таким id не найден",
        )
    if order.status != OrderStatus.PENDING or order.is_expired:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Заказ уже назначен или недоступен",
        )

    now = datetime.now(timezone.utc)
    order.courier_id = current_user.id
    order.status = OrderStatus.ASSIGNED
    order.accepted_at = now

    queue_entry = OrderQueue(
        order_id=order.id,
        courier_id=current_user.id,
        status=OrderQueueStatus.ACCEPTED,
        priority=order.priority,
        distance_km=0.0,
        offered_at=now,
        expires_at=now + timedelta(minutes=30),
        responded_at=now,
    )
    db.add(queue_entry)

    addr = order.pickup_address
    addr_str = ""
    if addr:
        addr_str = f"\nАдрес: {addr.street}, {addr.house_number}"
        if addr.apartment:
            addr_str += f", кв. {addr.apartment}"

    garbage_label = GARBAGE_TYPE_LABELS.get(str(order.garbage_type), str(order.garbage_type))
    notification_message = (
        f"{garbage_label}, {order.number_of_bags} мешк.\n"
        f"Цена: {order.final_price} руб.{addr_str}"
    )
    if order.description:
        notification_message += f"\n{order.description}"

    notification_courier = Notification(
        user_id=current_user.id,
        order_id=order.id,
        notification_type=NotificationType.ORDER_ASSIGNED,
        channel=NotificationChannel.IN_APP,
        title="Заказ принят",
        message=notification_message,
        sent_at=datetime.now(timezone.utc),
    )
    db.add(notification_courier)

    client_message = (
        f"Курьер: {current_user.first_name} {current_user.last_name}\n"
        f"Телефон: {current_user.phone or 'не указан'}\n"
        f"Рейтинг: {current_user.rating:.1f}★"
    )

    notification_client = Notification(
        user_id=order.client_id,
        order_id=order.id,
        notification_type=NotificationType.ORDER_ASSIGNED,
        channel=NotificationChannel.IN_APP,
        title="Заказ принят курьером",
        message=client_message,
        sent_at=datetime.now(timezone.utc),
    )
    db.add(notification_client)

    await db.flush()

    ws_message_courier = create_notification_message({
        "id": notification_courier.id,
        "title": notification_courier.title,
        "message": notification_courier.message,
        "priority": "HIGH",
        "created_at": notification_courier.sent_at,
    })
    await manager.send_personal_message(current_user.id, ws_message_courier)

    from app.websocket.schemas import create_order_assigned_message
    ws_message_client = create_order_assigned_message(
        order_id=order.id,
        courier_name=f"{current_user.first_name} {current_user.last_name}",
        courier_phone=current_user.phone or "не указан",
        courier_rating=current_user.rating,
        message=client_message
    )
    await manager.send_personal_message(order.client_id, ws_message_client)

    await db.commit()
    await db.refresh(order)

    if order.client_id:
        client_stmt = select(User).where(User.id == order.client_id)
        client_result = await db.execute(client_stmt)
        client_user = client_result.scalar_one_or_none()

        if client_user and client_user.telegram_id:
            courier_name = f"{current_user.first_name} {current_user.last_name}"
            notify_order_accepted.delay(client_user.telegram_id, courier_name)
    await get_redis().delete("orders:available")
    return order

@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: UUID,
    data: OrderStatusUpdate,
    current_user: User = Depends(require_order_operator),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.orm import joinedload

    stmt = select(Order).options(
        joinedload(Order.client),
        joinedload(Order.courier),
        joinedload(Order.pickup_address),
    ).where(Order.id == order_id).with_for_update(of=Order)
    result = await db.execute(stmt)
    order = result.unique().scalar_one_or_none()

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заказ не найден или не назначен на вас",
        )

    if current_user.role != UserRole.ADMIN and order.courier_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Этот заказ не назначен на вас",
        )

    from app.websocket import manager
    from app.websocket.schemas import create_order_status_message

    if data.status == OrderStatus.IN_PROGRESS:
        if order.status != OrderStatus.ASSIGNED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Заказ должен быть в статусе ASSIGNED",
            )
        old_status = str(order.status)
        order.status = OrderStatus.IN_PROGRESS
        order.started_at = datetime.now(timezone.utc)

        ws_message = create_order_status_message(
            order_id=order.id,
            status="IN_PROGRESS",
            message=f"Курьер начал выполнение заказа и направляется к вам",
            old_status=old_status
        )
        await manager.send_personal_message(order.client_id, ws_message)

    elif data.status == OrderStatus.ARRIVED:
        if order.status != OrderStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Заказ должен быть в статусе IN_PROGRESS",
            )
        old_status = str(order.status)
        order.status = OrderStatus.ARRIVED
        order.arrived_at = datetime.now(timezone.utc)

        ws_message = create_order_status_message(
            order_id=order.id,
            status="ARRIVED",
            message=f"Курьер прибыл на место. Ожидайте звонка в дверь!",
            old_status=old_status
        )
        await manager.send_personal_message(order.client_id, ws_message)

    elif data.status == OrderStatus.COMPLETED:
        if order.status not in [OrderStatus.IN_PROGRESS, OrderStatus.ARRIVED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Заказ должен быть в статусе IN_PROGRESS или ARRIVED",
            )
        old_status = str(order.status)
        order.status = OrderStatus.COMPLETED
        order.completed_at = datetime.now(timezone.utc)

        if order.courier_id:
            courier_stmt = select(User).where(User.id == order.courier_id)
            courier_result = await db.execute(courier_stmt)
            courier = courier_result.scalar_one_or_none()
            if courier:
                courier.completed_orders += 1

        ws_message_client = create_order_status_message(
            order_id=order.id,
            status="COMPLETED",
            message=f"Заказ выполнен! Спасибо за использование EcoHaul",
            old_status=old_status
        )
        await manager.send_personal_message(order.client_id, ws_message_client)
        if order.client_id:
            completed_client_stmt = select(User).where(User.id == order.client_id)
            completed_client_result = await db.execute(completed_client_stmt)
            completed_client = completed_client_result.scalar_one_or_none()
            if completed_client and completed_client.telegram_id:
                notify_order_completed.delay(completed_client.telegram_id)
        ws_message_courier = create_order_status_message(
            order_id=order.id,
            status="COMPLETED",
            message=f"Заказ успешно завершён! Отличная работа.",
            old_status=old_status
        )
        await manager.send_personal_message(current_user.id, ws_message_courier)

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недопустимый статус",
        )

    await db.commit()

    stmt_refresh = select(Order).options(
        joinedload(Order.client),
        joinedload(Order.courier),
        joinedload(Order.pickup_address),
    ).where(Order.id == order_id)
    result_refresh = await db.execute(stmt_refresh)
    order = result_refresh.unique().scalar_one()

    return order

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):

    stmt = select(Order).where(
        Order.id == order_id,
    ).options(selectinload(Order.pickup_address))
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заказ с таким id не найден",
        )

    if current_user.role == UserRole.ADMIN:
        pass
    elif current_user.role == UserRole.COURIER:
        if order.courier_id != current_user.id and order.status != OrderStatus.PENDING:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа")
    else:
        if order.client_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа")

    return order

@router.patch("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: UUID,
    data: OrderCancel,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.orm import joinedload

    stmt = select(Order).where(
        Order.id == order_id,
    ).with_for_update(of=Order)
    if current_user.role != UserRole.ADMIN:
        stmt = stmt.where(Order.client_id == current_user.id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заказ не найден или не принадлежит вам",
        )

    if order.status not in [OrderStatus.PENDING, OrderStatus.ASSIGNED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Заказ нельзя отменить в текущем статусе. Можно отменить только заказы в статусе 'Ожидает' или 'Назначен'",
        )

    courier_id = order.courier_id

    order.status = OrderStatus.CANCELLED
    order.cancelled_at = datetime.now(timezone.utc)
    order.cancelled_by_id = current_user.id
    order.cancellation_reason = data.reason

    await db.commit()

    if courier_id:
        from app.websocket import manager
        from app.websocket.schemas import create_order_status_message

        ws_message = create_order_status_message(
            order_id=order.id,
            status="CANCELLED",
            message=f"Заказ отменён клиентом. Причина: {data.reason or 'Не указана'}"
        )
        await manager.send_personal_message(courier_id, ws_message)

    stmt_refresh = select(Order).options(
        joinedload(Order.client),
        joinedload(Order.courier),
        joinedload(Order.pickup_address),
    ).where(Order.id == order_id)
    result_refresh = await db.execute(stmt_refresh)
    order = result_refresh.unique().scalar_one()

    await get_redis().delete("orders:available")
    return order

@router.patch("/{order_id}/assign-courier", response_model=OrderResponse)
async def assign_courier_to_order(
        order_id: UUID,
        courier_id: UUID = Query(...),
        current_user: User = Depends(require_admin),
        db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.orm import joinedload

    stmt = select(Order).where(Order.id == order_id).with_for_update(of=Order)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заказ не найден",
        )

    if order.status != OrderStatus.PENDING or order.is_expired:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Заказ должен быть в статусе PENDING",
        )

    from app.models.enums import UserRole
    courier_stmt = select(User).where(User.id == courier_id, User.role == UserRole.COURIER)
    courier_result = await db.execute(courier_stmt)
    courier = courier_result.scalar_one_or_none()

    if courier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Курьер не найден",
        )

    now = datetime.now(timezone.utc)
    order.courier_id = courier_id
    order.status = OrderStatus.ASSIGNED
    order.accepted_at = now

    courier.total_orders += 1

    await db.commit()

    stmt_refresh = select(Order).options(
        joinedload(Order.client),
        joinedload(Order.courier),
        joinedload(Order.pickup_address),
    ).where(Order.id == order_id)
    result_refresh = await db.execute(stmt_refresh)
    order = result_refresh.unique().scalar_one()

    await get_redis().delete("orders:available")
    return order

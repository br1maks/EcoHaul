
from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime

from pydantic import Field, field_validator, model_validator

from app.models.enums import OrderStatus, GarbageType, SubscriptionTier
from app.schemas.common import BaseSchema, UUIDMixin, TimestampMixin, SoftDeleteMixin
from app.schemas.address import AddressResponse

BASE_PRICE_PER_BAG = 5.0

SUBSCRIPTION_DISCOUNTS = {
    SubscriptionTier.FREE: 0.0,
    SubscriptionTier.BASIC: 0.20,
    SubscriptionTier.PREMIUM: 0.30,
}

def calculate_price(
    number_of_bags: int,
    subscription_tier: Optional[SubscriptionTier] = None,
) -> tuple[float, float, float]:
    price_before_discount = number_of_bags * BASE_PRICE_PER_BAG

    tier = subscription_tier or SubscriptionTier.FREE
    discount_rate = SUBSCRIPTION_DISCOUNTS.get(tier, 0.0)
    discount_amount = round(price_before_discount * discount_rate, 2)

    final_price = round(price_before_discount - discount_amount, 2)

    return price_before_discount, discount_amount, final_price

def validate_status_transition(current_status: OrderStatus, new_status: OrderStatus) -> bool:
    if current_status == new_status:
        return True

    if current_status in [OrderStatus.COMPLETED, OrderStatus.CANCELLED]:
        return False

    allowed_transitions = {
        OrderStatus.PENDING: [OrderStatus.ASSIGNED, OrderStatus.CANCELLED],
        OrderStatus.ASSIGNED: [OrderStatus.IN_PROGRESS, OrderStatus.CANCELLED],
        OrderStatus.IN_PROGRESS: [OrderStatus.COMPLETED, OrderStatus.CANCELLED],
    }

    return new_status in allowed_transitions.get(current_status, [])

class OrderBase(BaseSchema):

    garbage_type: GarbageType = Field(
        GarbageType.HOUSEHOLD,
        description="Тип мусора для вывоза",
        examples=[GarbageType.HOUSEHOLD],
    )
    number_of_bags: int = Field(
        ...,
        ge=1,
        le=10,
        description="Количество мешков (1-10)",
        examples=[1, 2, 3, 5],
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Дополнительное описание для курьера",
        examples=[
            "Мешки стоят возле подъезда",
            "Перезвоните за 10 минут до приезда",
            None,
        ],
    )
    scheduled_time: Optional[datetime] = Field(
        None,
        description="Запланированное время приезда курьера (опционально)",
        examples=[None, "2025-11-09T14:00:00+03:00"],
    )

    @field_validator("garbage_type")
    @classmethod
    def validate_garbage_type(cls, v: GarbageType) -> GarbageType:
        if v != GarbageType.HOUSEHOLD:
            raise ValueError(
                f"В текущей версии поддерживается только бытовой мусор (HOUSEHOLD). "
                f"Тип {v.value} будет добавлен в следующих версиях."
            )
        return v

    @field_validator("number_of_bags")
    @classmethod
    def validate_number_of_bags(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Минимальное количество мешков: 1")
        if v > 10:
            raise ValueError(
                f"Максимальное количество мешков для одного заказа: 10. "
                f"Вы указали: {v}. Для больших объёмов создайте несколько заказов."
            )
        return v

    @field_validator("scheduled_time")
    @classmethod
    def validate_scheduled_time(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is None:
            return None

        now = datetime.now(v.tzinfo)

        if v < now:
            raise ValueError("Запланированное время не может быть в прошлом")

        min_time = now.replace(minute=now.minute + 30)
        if v < min_time:
            raise ValueError(
                f"Запланированное время должно быть минимум через 30 минут от сейчас. "
                f"Сейчас: {now.strftime('%H:%M')}, минимальное время: {min_time.strftime('%H:%M')}"
            )

        max_time = now.replace(day=now.day + 7)
        if v > max_time:
            raise ValueError(
                f"Запланированное время не может быть более чем через 7 дней. "
                f"Максимальная дата: {max_time.strftime('%Y-%m-%d %H:%M')}"
            )

        return v

class OrderCreate(OrderBase):

    pickup_address_id: UUID = Field(
        ...,
        description="UUID адреса откуда забрать мусор",
        examples=["123e4567-e89b-12d3-a456-426614174000"],
    )

    @model_validator(mode="after")
    def validate_order(self):
        return self

class OrderUpdate(BaseSchema):

    status: Optional[OrderStatus] = Field(
        None,
        description="Новый статус заказа",
        examples=[OrderStatus.ASSIGNED, OrderStatus.IN_PROGRESS, OrderStatus.COMPLETED],
    )
    courier_id: Optional[UUID] = Field(
        None,
        description="UUID курьера (для назначения)",
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Обновлённое описание",
    )
    scheduled_time: Optional[datetime] = Field(
        None,
        description="Новое запланированное время",
    )
    distance_km: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Фактическое расстояние в км (при завершении)",
        examples=[1.5, 2.3, 5.0],
    )
    cancellation_reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Причина отмены заказа",
        examples=["Передумал", "Курьер не приехал вовремя", "Ошибка в адресе"],
    )

    @field_validator("scheduled_time")
    @classmethod
    def validate_scheduled_time(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is None:
            return None

        now = datetime.now(v.tzinfo)

        if v < now:
            raise ValueError("Запланированное время не может быть в прошлом")

        min_time = now.replace(minute=now.minute + 30)
        if v < min_time:
            raise ValueError("Запланированное время должно быть минимум через 30 минут")

        max_time = now.replace(day=now.day + 7)
        if v > max_time:
            raise ValueError("Запланированное время не может быть более чем через 7 дней")

        return v

    @model_validator(mode="after")
    def validate_update(self):
        if self.status == OrderStatus.CANCELLED and not self.cancellation_reason:
            raise ValueError("При отмене заказа необходимо указать причину (cancellation_reason)")

        if self.distance_km is not None and self.status != OrderStatus.COMPLETED:
            raise ValueError("Расстояние (distance_km) можно указать только при завершении заказа")

        return self

class OrderResponse(UUIDMixin, TimestampMixin, SoftDeleteMixin, OrderBase):

    client_id: UUID = Field(..., description="UUID клиента")
    courier_id: Optional[UUID] = Field(None, description="UUID курьера (если назначен)")
    pickup_address_id: UUID = Field(..., description="UUID адреса")
    pickup_address: Optional[AddressResponse] = Field(None, description="Адрес забора мусора")
    status: OrderStatus = Field(..., description="Текущий статус заказа")

    price_before_discount: float = Field(..., description="Цена до скидки (BYN)", ge=0.0)
    discount_amount: float = Field(..., description="Сумма скидки (BYN)", ge=0.0)
    final_price: float = Field(..., description="Финальная цена после скидки (BYN)", ge=0.0)
    subscription_tier_used: Optional[SubscriptionTier] = Field(
        None,
        description="Использованный уровень подписки при создании заказа",
    )

    distance_km: Optional[float] = Field(None, description="Фактическое расстояние (км)", ge=0.0)

    accepted_at: Optional[datetime] = Field(None, description="Когда курьер принял заказ")
    started_at: Optional[datetime] = Field(None, description="Когда курьер начал выполнение")
    completed_at: Optional[datetime] = Field(None, description="Когда заказ завершён")
    cancelled_at: Optional[datetime] = Field(None, description="Когда заказ отменён")

    cancellation_reason: Optional[str] = Field(None, description="Причина отмены")
    cancelled_by_id: Optional[UUID] = Field(None, description="Кто отменил заказ")

    is_pending: bool = Field(..., description="Ожидает назначения курьера")
    is_active: bool = Field(..., description="Активный заказ (PENDING/ASSIGNED/IN_PROGRESS)")
    is_completed: bool = Field(..., description="Заказ завершён")
    has_discount: bool = Field(..., description="Есть скидка")
    discount_percentage: float = Field(..., description="Процент скидки", ge=0.0, le=100.0)
    duration_minutes: Optional[int] = Field(None, description="Длительность выполнения (минуты)")

    courier_telegram_link: Optional[str] = Field(
        None,
        description="Ссылка для связи с курьером в Telegram",
        examples=["tg://user?id=123456789", "https://t.me/courier_ivan"],
    )
    courier_phone: Optional[str] = Field(
        None,
        description="Номер телефона курьера (если указан)",
        examples=["+375291234567", None],
    )
    courier_phone_display: Optional[str] = Field(
        None,
        description="Отформатированный номер телефона курьера",
        examples=["+375 (29) 123-45-67", None],
    )

    client_telegram_link: Optional[str] = Field(
        None,
        description="Ссылка для связи с клиентом в Telegram",
        examples=["tg://user?id=987654321", "https://t.me/client_maria"],
    )
    client_phone: Optional[str] = Field(
        None,
        description="Номер телефона клиента (если указан)",
        examples=["+375297654321", None],
    )
    client_phone_display: Optional[str] = Field(
        None,
        description="Отформатированный номер телефона клиента",
        examples=["+375 (29) 765-43-21", None],
    )

    @model_validator(mode="before")
    @classmethod
    def calculate_computed_fields(cls, data: Any) -> Any:
        if hasattr(data, "__dict__") and hasattr(data, "id"):
            status_value = data.status
            if hasattr(status_value, "value"):
                status_value = status_value.value
            status_str = str(status_value) if status_value else "PENDING"

            try:
                is_pending = getattr(data, "is_pending", None)
            except:
                is_pending = None
            try:
                is_active = getattr(data, "is_active", None)
            except:
                is_active = None
            try:
                is_completed = getattr(data, "is_completed", None)
            except:
                is_completed = None
            try:
                has_discount = getattr(data, "has_discount", None)
            except:
                has_discount = None
            try:
                discount_percentage = getattr(data, "discount_percentage", None)
            except:
                discount_percentage = None
            try:
                duration_minutes = getattr(data, "duration_minutes", None)
            except:
                duration_minutes = None

            model_data = {
                "id": data.id,
                "created_at": data.created_at,
                "updated_at": getattr(data, "updated_at", None),
                "deleted_at": getattr(data, "deleted_at", None),
                "client_id": data.client_id,
                "courier_id": data.courier_id,
                "pickup_address_id": data.pickup_address_id,
                "pickup_address": getattr(data, "pickup_address", None),
                "garbage_type": data.garbage_type,
                "number_of_bags": data.number_of_bags,
                "description": data.description,
                "status": status_str,
                "price_before_discount": float(data.price_before_discount) if data.price_before_discount else 0.0,
                "discount_amount": float(data.discount_amount) if data.discount_amount else 0.0,
                "final_price": float(data.final_price) if data.final_price else 0.0,
                "subscription_tier_used": data.subscription_tier_used,
                "distance_km": float(data.distance_km) if data.distance_km else None,
                "scheduled_time": data.scheduled_time,
                "accepted_at": getattr(data, "accepted_at", None),
                "started_at": getattr(data, "started_at", None),
                "completed_at": getattr(data, "completed_at", None),
                "cancelled_at": getattr(data, "cancelled_at", None),
                "cancellation_reason": getattr(data, "cancellation_reason", None),
                "cancelled_by_id": getattr(data, "cancelled_by_id", None),
                "is_pending": is_pending if is_pending is not None else (status_str == "PENDING"),
                "is_active": is_active if is_active is not None else (status_str in ["PENDING", "ASSIGNED", "IN_PROGRESS"]),
                "is_completed": is_completed if is_completed is not None else (status_str == "COMPLETED"),
                "has_discount": has_discount if has_discount is not None else (float(data.discount_amount or 0) > 0),
                "discount_percentage": discount_percentage if discount_percentage is not None else 0.0,
                "duration_minutes": duration_minutes,
            }

            show_contacts = status_str in ["ASSIGNED", "IN_PROGRESS"]

            if show_contacts and hasattr(data, "courier") and data.courier:
                courier = data.courier
                if courier.telegram_username:
                    model_data["courier_telegram_link"] = f"https://t.me/{courier.telegram_username}"
                elif courier.telegram_id:
                    model_data["courier_telegram_link"] = f"tg://user?id={courier.telegram_id}"
                else:
                    model_data["courier_telegram_link"] = None

                if courier.phone:
                    model_data["courier_phone"] = courier.phone
                    model_data["courier_phone_display"] = format_phone_display(courier.phone)
                else:
                    model_data["courier_phone"] = None
                    model_data["courier_phone_display"] = None
            else:
                model_data["courier_telegram_link"] = None
                model_data["courier_phone"] = None
                model_data["courier_phone_display"] = None

            if show_contacts and hasattr(data, "client") and data.client:
                client = data.client
                if client.telegram_username:
                    model_data["client_telegram_link"] = f"https://t.me/{client.telegram_username}"
                elif client.telegram_id:
                    model_data["client_telegram_link"] = f"tg://user?id={client.telegram_id}"
                else:
                    model_data["client_telegram_link"] = None

                if client.phone:
                    model_data["client_phone"] = client.phone
                    model_data["client_phone_display"] = format_phone_display(client.phone)
                else:
                    model_data["client_phone"] = None
                    model_data["client_phone_display"] = None
            else:
                model_data["client_telegram_link"] = None
                model_data["client_phone"] = None
                model_data["client_phone_display"] = None

            data = model_data

        elif isinstance(data, dict):
            status_val = data.get("status", "")
            status_str = status_val.value if hasattr(status_val, "value") else str(status_val)

            if "is_pending" not in data:
                data["is_pending"] = status_str == "PENDING"
            if "is_active" not in data:
                data["is_active"] = status_str in ["PENDING", "ASSIGNED", "IN_PROGRESS"]
            if "is_completed" not in data:
                data["is_completed"] = status_str == "COMPLETED"
            if "has_discount" not in data:
                data["has_discount"] = float(data.get("discount_amount", 0) or 0) > 0
            if "discount_percentage" not in data:
                price_before = float(data.get("price_before_discount", 0) or 0)
                discount = float(data.get("discount_amount", 0) or 0)
                if price_before > 0:
                    data["discount_percentage"] = round((discount / price_before) * 100, 2)
                else:
                    data["discount_percentage"] = 0.0

            if "courier_telegram_link" not in data:
                data["courier_telegram_link"] = None
            if "courier_phone" not in data:
                data["courier_phone"] = None
            if "courier_phone_display" not in data:
                data["courier_phone_display"] = None
            if "client_telegram_link" not in data:
                data["client_telegram_link"] = None
            if "client_phone" not in data:
                data["client_phone"] = None
            if "client_phone_display" not in data:
                data["client_phone_display"] = None

        return data

def format_phone_display(phone: str) -> str:
    if not phone or len(phone) < 11:
        return phone

    if phone.startswith("+375") and len(phone) == 13:
        return f"+375 ({phone[4:6]}) {phone[6:9]}-{phone[9:11]}-{phone[11:13]}"

    if phone.startswith("+7") and len(phone) == 12:
        return f"+7 ({phone[2:5]}) {phone[5:8]}-{phone[8:10]}-{phone[10:12]}"

    return phone

class OrderBrief(UUIDMixin, BaseSchema):

    status: OrderStatus = Field(..., description="Текущий статус заказа")
    number_of_bags: int = Field(..., description="Количество мешков")
    final_price: float = Field(..., description="Финальная цена (BYN)")
    created_at: datetime = Field(..., description="Когда создан заказ")
    scheduled_time: Optional[datetime] = Field(None, description="Запланированное время")

class OrderStatusUpdate(BaseSchema):
    status: OrderStatus = Field(..., description="Новый статус заказа")

class OrderAssignment(BaseSchema):
    courier_id: UUID = Field(..., description="ID курьера для назначения")

class OrderCancellation(BaseSchema):
    cancelled_by_id: UUID = Field(..., description="ID пользователя, отменившего заказ")
    cancellation_reason: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Причина отмены (обязательна, минимум 10 символов)"
    )

"""
ЧТО МЫ СОЗДАЛИ:

1. OrderBase - базовые поля заказа
   └─ Валидация: garbage_type (только HOUSEHOLD), number_of_bags (1-10), scheduled_time
   └─ Все поля для создания заказа клиентом

2. OrderCreate - для создания заказа
   └─ Дополнительно: pickup_address_id
   └─ Автоматический расчёт цены в business logic

3. OrderUpdate - для обновления заказа
   └─ Все поля опциональные
   └─ Валидация переходов статусов
   └─ Валидация отмены (нужна причина)

4. OrderResponse - полный ответ с computed fields
   └─ Все поля из модели
   └─ Computed fields: is_pending, is_active, is_completed, has_discount, discount_percentage, duration_minutes
   └─ Контактная информация: courier_telegram_link, courier_phone, client_telegram_link, client_phone
   └─ Для отображения деталей заказа

5. OrderBrief - краткая версия для списков
   └─ Только id, status, number_of_bags, final_price, created_at, scheduled_time
   └─ Без nested objects и computed fields

6. OrderStatusUpdate - для обновления только статуса
   └─ status (required)
   └─ Используется в PATCH /api/orders/{id}/status

7. OrderAssignment - для назначения курьера
   └─ courier_id (required)
   └─ Используется в POST /api/orders/{id}/assign

8. OrderCancellation - для отмены заказа
   └─ cancelled_by_id (required)
   └─ cancellation_reason (required, min 10 символов)
   └─ Используется в POST /api/orders/{id}/cancel

ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ:
- calculate_price() - расчёт цены с учётом подписки
- validate_status_transition() - проверка допустимости перехода статусов
- format_phone_display() - форматирование телефона для отображения

PRICING ФОРМУЛА:
- Базовая цена = number_of_bags × 5 BYN
- Скидка: FREE=0%, BASIC=20%, PREMIUM=30%

ЖИЗНЕННЫЙ ЦИКЛ:
PENDING → ASSIGNED → IN_PROGRESS → COMPLETED
    ↓          ↓            ↓
CANCELLED  CANCELLED   CANCELLED

КОНТАКТНАЯ ИНФОРМАЦИЯ (клиент ↔ курьер):
- Telegram Deep Links: tg://user?id={id} или t.me/{username}
- Телефон: tel:{phone} (если указан)
- Показываются только при ASSIGNED/IN_PROGRESS

ПАТТЕРНЫ:
- Base: общие поля + валидация
- Create: Base + pickup_address_id
- Update: частичная версия + status, courier_id, distance_km, cancellation
- Response: Base + все поля модели + computed fields + контакты
- Brief: минимальный набор для списков

ИСПОЛЬЗОВАНИЕ:
```python
# Создание заказа
order = OrderCreate(
    pickup_address_id=address.id,
    number_of_bags=3,
    garbage_type=GarbageType.HOUSEHOLD
)
# → POST /api/orders
# → Цена рассчитывается автоматически

# Курьер принимает заказ
update = OrderUpdate(
    status=OrderStatus.ASSIGNED,
    courier_id=courier.id
)
# → PATCH /api/orders/{id}
# → accepted_at = now

# Получение деталей
order: OrderResponse = await service.get_order(order_id)
print(f"Статус: {order.status}")
print(f"Связаться с курьером: {order.courier_telegram_link}")
```

ДОСТУП:
- CLIENT: Создание, просмотр своих, отмена своих
- COURIER: Просмотр доступных (PENDING), принятие, обновление статуса, завершение
- ADMIN: Полный CRUD, назначение курьеров
"""

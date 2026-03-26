
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import EmailStr, Field, field_validator, model_validator

from app.models.enums import UserRole, CourierStatus
from app.schemas.common import BaseSchema, UUIDMixin, TimestampMixin, SoftDeleteMixin

class UserBase(BaseSchema):

    first_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )
    last_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )
    phone: Optional[str] = Field(
        None,
        min_length=10,
        max_length=20,
        pattern=r"^\+?\d{10,20}$",
    )
    email: Optional[EmailStr] = Field(
        None,
    )
    age: Optional[int] = Field(
        None,
        ge=18,
        le=100,
    )

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v

        v = v.replace(" ", "").replace("-", "")

        if not v.startswith("+"):
            raise ValueError("Номер телефона должен начинаться с +")

        if not v[1:].isdigit():
            raise ValueError("Номер телефона должен содержать только цифры после +")

        if len(v) < 11 or len(v) > 21:
            raise ValueError("Номер телефона должен содержать 10-20 цифр")

        return v

class UserCreate(UserBase):

    telegram_id: int = Field(
        ...,
        gt=0,
        examples=[123456789, 987654321],
    )
    telegram_username: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_]+$",
    )
    telegram_mini_app_user_id: Optional[str] = Field(
        None,
        max_length=255,
        description="ID пользователя из Telegram Mini App OAuth",
        examples=["tma_user_abc123xyz"],
    )
    role: UserRole = Field(
        UserRole.CLIENT,
    )
    passport_number: Optional[str] = Field(
        None,
        min_length=5,
        max_length=20,
        examples=["AB1234567", "MP3456789"],
    )

    @field_validator("telegram_username")
    @classmethod
    def validate_telegram_username(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.lstrip("@")
        if not v:
            return None

        return v

    @model_validator(mode="after")
    def validate_courier_fields(self):
        if self.role == UserRole.COURIER and not self.passport_number:
            raise ValueError("Для роли COURIER необходимо указать passport_number")
        return self

class UserUpdate(BaseSchema):

    first_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
    )
    last_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
    )
    phone: Optional[str] = Field(
        None,
        min_length=10,
        max_length=20,
        pattern=r"^\+?\d{10,20}$",
    )
    email: Optional[EmailStr] = Field(
        None,
    )
    age: Optional[int] = Field(
        None,
        ge=18,
        le=100,
    )
    telegram_username: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
    )
    passport_number: Optional[str] = Field(
        None,
        min_length=5,
        max_length=20,
    )
    courier_status: Optional[CourierStatus] = Field(
        None,
        examples=[CourierStatus.ACTIVE, CourierStatus.OFFLINE, CourierStatus.ON_BREAK],
    )

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v

        v = v.replace(" ", "").replace("-", "")

        if not v.startswith("+"):
            raise ValueError("Номер телефона должен начинаться с +")

        if not v[1:].isdigit():
            raise ValueError("Номер телефона должен содержать только цифры")

        return v

    @field_validator("telegram_username")
    @classmethod
    def validate_telegram_username(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v

        v = v.lstrip("@")

        if not v:
            return None

        return v

class UserResponse(UUIDMixin, TimestampMixin, SoftDeleteMixin, UserBase):

    telegram_id: int = Field(..., description="ID пользователя в Telegram")
    telegram_username: Optional[str] = Field(None, description="Username в Telegram")
    telegram_mini_app_user_id: Optional[str] = Field(
        None, description="ID из Telegram Mini App"
    )

    role: UserRole = Field(..., description="Роль пользователя")
    courier_status: Optional[CourierStatus] = Field(
        None, description="Статус курьера (только для role=COURIER)"
    )

    rating: float = Field(
        ...,
        ge=1.0,
        le=5.0,
        description="Средний рейтинг (1.0-5.0)",
        examples=[4.5, 5.0, 3.8],
    )
    total_orders: int = Field(
        ..., ge=0, description="Общее количество заказов", examples=[0, 10, 100]
    )
    completed_orders: int = Field(
        ..., ge=0, description="Количество завершённых заказов", examples=[0, 8, 95]
    )

    is_verified: bool = Field(
        ..., description="Верифицирован ли пользователь (проверка паспорта)"
    )
    is_active: bool = Field(..., description="Активен ли аккаунт")
    passport_number: Optional[str] = Field(None, description="Номер паспорта")

    full_name: str = Field(
        ..., description="Полное имя (first_name + last_name)", examples=["Максим Петров"]
    )
    completion_rate: float = Field(
        ...,
        ge=0,
        le=100,
        description="Процент завершённых заказов",
        examples=[0.0, 80.0, 100.0],
    )

    @model_validator(mode="before")
    @classmethod
    def calculate_computed_fields(cls, data):
        if hasattr(data, "full_name"):
            if not isinstance(data, dict):
                data_dict = {
                    **{k: getattr(data, k) for k in data.__dict__ if not k.startswith("_")},
                    "full_name": data.full_name,
                    "completion_rate": data.completion_rate,
                }
                return data_dict

        if isinstance(data, dict):
            if "full_name" not in data:
                data["full_name"] = f"{data.get('first_name', '')} {data.get('last_name', '')}"

            if "completion_rate" not in data:
                total = data.get("total_orders", 0)
                completed = data.get("completed_orders", 0)
                data["completion_rate"] = round((completed / total) * 100, 2) if total > 0 else 0.0

        return data

class UserBrief(UUIDMixin, BaseSchema):

    telegram_id: int = Field(..., description="ID пользователя в Telegram")
    telegram_username: Optional[str] = Field(None, description="Username в Telegram")

    first_name: str = Field(..., description="Имя")
    last_name: str = Field(..., description="Фамилия")
    full_name: str = Field(..., description="Полное имя")

    role: UserRole = Field(..., description="Роль пользователя")
    courier_status: Optional[CourierStatus] = Field(
        None, description="Статус курьера (только для COURIER)"
    )

    rating: float = Field(
        ..., ge=1.0, le=5.0, description="Средний рейтинг", examples=[4.5, 5.0]
    )
    total_orders: int = Field(
        ..., ge=0, description="Общее количество заказов", examples=[0, 10]
    )

    is_active: bool = Field(..., description="Активен ли аккаунт")

    @model_validator(mode="before")
    @classmethod
    def add_full_name(cls, data):
        if hasattr(data, "full_name"):
            if not isinstance(data, dict):
                data_dict = {
                    **{k: getattr(data, k) for k in data.__dict__ if not k.startswith("_")},
                    "full_name": data.full_name,
                }
                return data_dict

        if isinstance(data, dict) and "full_name" not in data:
            data["full_name"] = f"{data.get('first_name', '')} {data.get('last_name', '')}"

        return data

"""
ЧТО МЫ СОЗДАЛИ:

1. UserBase - базовые поля (first_name, last_name, phone, email, age)
   └─ Валидация телефона: +, только цифры, 10-20 символов

2. UserCreate - для регистрации через Telegram
   └─ Дополнительно: telegram_id, role, passport_number
   └─ Валидация: курьерам нужен паспорт

3. UserUpdate - для обновления профиля
   └─ Все поля опциональные (частичное обновление)
   └─ Нельзя обновить telegram_id, role

4. UserResponse - полный ответ
   └─ Все поля из модели
   └─ Computed fields: full_name, completion_rate

5. UserBrief - краткая версия для списков
   └─ Только публичные данные
   └─ Без финансов, email, phone

ПАТТЕРНЫ:
- Base: общие поля
- Create: Base + уникальные поля + бизнес-валидация
- Update: частичная версия Create (все Optional)
- Response: Base + все поля модели + computed fields
- Brief: минимальный набор для списков

ИСПОЛЬЗОВАНИЕ:
```python
# Создание
user = UserCreate(telegram_id=123, first_name="Максим", last_name="Петров")
user_db = User(**user.model_dump())
await session.add(user_db)

# Чтение
user_db = await session.get(User, user_id)
user_response = UserResponse.model_validate(user_db)

# Обновление
update_data = UserUpdate(phone="+375291234567")
for field, value in update_data.model_dump(exclude_unset=True).items():
    setattr(user_db, field, value)

# Список
users = await session.execute(select(User).limit(20))
users_brief = [UserBrief.model_validate(u) for u in users.scalars()]
```
"""

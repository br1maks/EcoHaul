from typing import Optional
from uuid import UUID

from sqlalchemy import String, Integer, BigInteger, Numeric, Float, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, IDMixin, TimestampMixin, SoftDeleteMixin
from .enums import UserRole, CourierStatus

class User(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
    )

    telegram_username: Mapped[Optional[str]] = mapped_column(
        String(100),
        unique=False,
        nullable=True,
        index=True,
        doc="Telegram username (@username)"
    )

    telegram_mini_app_user_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    phone: Mapped[Optional[str]] = mapped_column(
        String(20),
        unique=True,
        nullable=True,
        index=True,
        doc="Номер телефона в международном формате E.164 (от Telegram API)"
    )

    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        doc="Email для OAuth2 (опционально)"
    )

    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Хеш пароля для подтверждения взятия заказа курьером"
    )

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    age: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    role: Mapped[UserRole] = mapped_column(
        String(20),
        default=UserRole.CLIENT,
        nullable=False,
        index=True,
    )

    courier_status: Mapped[Optional[CourierStatus]] = mapped_column(
        String(20),
        default=CourierStatus.OFFLINE,
        nullable=True,
    )
    
    rating: Mapped[float] = mapped_column(
        Float,
        default=5.0,
        nullable=False,
    )
    
    total_orders: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Всего заказов (для курьеров - выполнено)"
    )
    
    completed_orders: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Успешно завершённых заказов"
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Верифицирован ли номер телефона (для курьеров)"
    )

    is_telegram_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Подтверждён ли Telegram аккаунт"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Активен ли пользователь (может быть заблокирован)"
    )

    passport_number: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        doc="Номер паспорта (только для курьеров)"
    )

    addresses = relationship(
        "Address",
        back_populates="user",
        doc="Список адресов пользователя"
    )

    orders_as_client = relationship(
        "Order",
        foreign_keys="Order.client_id",
        back_populates="client",
        doc="Заказы которые этот пользователь создал"
    )

    orders_as_courier = relationship(
        "Order",
        foreign_keys="Order.courier_id",
        back_populates="courier",
        doc="Заказы которые этот курьер выполняет"
    )
    
    subscription = relationship(
        "Subscription",
        back_populates="user",
        uselist=False,
        doc="Активная подписка пользователя"
    )

    verification_codes = relationship(
        "VerificationCode",
        back_populates="user",
        doc="Коды верификации отправленные пользователю"
    )

    payments = relationship(
        "Payment",
        back_populates="user",
        doc="История платежей"
    )

    reviews_given = relationship(
        "Review",
        foreign_keys="Review.reviewer_id",
        back_populates="reviewer",
        doc="Отзывы оставленные этим пользователем"
    )

    reviews_received = relationship(
        "Review",
        foreign_keys="Review.reviewee_id",
        back_populates="reviewee",
        doc="Отзывы полученные этим пользователем (если курьер)"
    )

    notifications = relationship(
        "Notification",
        back_populates="user",
        doc="Уведомления пользователя"
    )

    courier_shifts = relationship(
        "CourierShift",
        back_populates="courier",
    )

    courier_applications = relationship(
        "CourierApplication",
        back_populates="user",
        foreign_keys="CourierApplication.user_id",
        doc="Заявки на работу курьером"
    )

    __table_args__ = (
        Index("idx_users_role_active", "role", "is_active"),
        Index("idx_users_courier_status", "courier_status"),
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def completion_rate(self) -> float:
        if self.total_orders == 0:
            return 0.0
        return round((self.completed_orders / self.total_orders) * 100, 2)

    @property
    def is_courier(self) -> bool:
        return self.role == UserRole.COURIER

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, role={self.role}, full_name='{self.full_name}')>"
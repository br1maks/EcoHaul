from uuid import UUID
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, IDMixin, TimestampMixin
from .enums import CourierApplicationStatus

class CourierApplication(Base, IDMixin, TimestampMixin):
    __tablename__ = "courier_applications"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    user: Mapped["User"] = relationship(
        "User",
        back_populates="courier_applications",
        foreign_keys=[user_id]
    )

    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    has_transport: Mapped[bool] = mapped_column(default=False)
    transport_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    work_area: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[CourierApplicationStatus] = mapped_column(
        SQLEnum(CourierApplicationStatus),
        default=CourierApplicationStatus.PENDING,
        nullable=False
    )

    admin_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    reviewed_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[reviewed_by_id]
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    def __repr__(self) -> str:
        return f"<CourierApplication {self.id} user={self.user_id} status={self.status}>"

from typing import Optional
from uuid import UUID

from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry

from .base import Base, IDMixin, TimestampMixin, SoftDeleteMixin
from .enums import AddressLabel

class Address(Base, IDMixin, TimestampMixin, SoftDeleteMixin):

    __tablename__ = "addresses"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    location: Mapped[str] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=False,
    )
    latitude: Mapped[float] = mapped_column( 
        Float,
        nullable=False,
    )
    longitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Долгота (для удобного доступа без PostGIS функций)"
    )

    full_address: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    city: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Минск",
    )

    district: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    street: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    house_number: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    apartment: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )

    entrance: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    floor: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    label: Mapped[Optional[AddressLabel]] = mapped_column(
        String(20),
        nullable=True,

    )

    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    notes: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    yandex_geocoder_response: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
    )

    user = relationship(
        "User",
        back_populates="addresses",
    )

    orders = relationship(
        "Order",
        back_populates="pickup_address",
    )

    __table_args__ = (
        Index("idx_address_location", "location", postgresql_using="gist"),
        Index("idx_user_default_address", "user_id", "is_default"),
        Index("idx_address_district", "district"),
    )

    @property
    def short_address(self) -> str:
        parts = [self.street, self.house_number]

        if self.apartment:
            parts.append(f"кв. {self.apartment}")

        return ", ".join(parts)

    @property
    def full_address_with_details(self) -> str:
        parts = [self.full_address]

        if self.entrance:
            parts.append(f"подъезд {self.entrance}")

        if self.floor:
            parts.append(f"этаж {self.floor}")

        if self.apartment:
            parts.append(f"кв. {self.apartment}")

        return ", ".join(parts)

    @property
    def coordinates_tuple(self) -> tuple[float, float]:
        return (self.latitude, self.longitude)

    def __repr__(self) -> str:
        return (
            f"<Address(id={self.id}, user_id={self.user_id}, "
            f"short_address='{self.short_address}', district='{self.district}')>"
        )

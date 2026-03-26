
from typing import Optional
from sqlalchemy import String, Boolean, Text, Index
from sqlalchemy.orm import Mapped, mapped_column
from geoalchemy2 import Geometry
from .base import Base, IDMixin, TimestampMixin, SoftDeleteMixin

class ServiceZone(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "service_zones"

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    polygon: Mapped[str] = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        index=True,
        nullable=False
    )

    __table_args__ = (
        Index("idx_service_zone_polygon", "polygon", postgresql_using="gist"),
    )

    @property
    def is_available(self) -> bool:
        return self.is_active and self.deleted_at is None
    
    def __repr__(self) -> str:
        return f"<ServiceZone(id={self.id}, name='{self.name}', is_active={self.is_active})>"
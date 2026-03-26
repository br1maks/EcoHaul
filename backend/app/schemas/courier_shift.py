
from typing import Optional, Any
from uuid import UUID
from datetime import datetime

from pydantic import Field, field_validator, model_validator

from app.schemas.common import BaseSchema, UUIDMixin, TimestampMixin

class CourierShiftBase(BaseSchema):
    courier_id: UUID
    started_at: datetime
    ended_at: Optional[datetime] = None
    orders_completed: int = Field(default=0, ge=0, le=1000)
    start_location_lat: Optional[float] = Field(None, ge=-90.0, le=90.0)
    start_location_lon: Optional[float] = Field(None, ge=-180.0, le=180.0)
    end_location_lat: Optional[float] = Field(None, ge=-90.0, le=90.0)
    end_location_lon: Optional[float] = Field(None, ge=-180.0, le=180.0)
    total_distance_km: float = Field(default=0.0, ge=0.0, le=10000.0)
    break_duration_minutes: int = Field(default=0, ge=0, le=1440)
    notes: Optional[str] = None
    early_end_reason: Optional[str] = Field(None, max_length=500)

    @model_validator(mode="after")
    def validate_shift_logic(self):
        if self.ended_at and self.ended_at <= self.started_at:
            raise ValueError("ended_at должен быть позже started_at")

        if self.ended_at:
            if self.start_location_lat and self.start_location_lon:
                if not self.end_location_lat or not self.end_location_lon:
                    raise ValueError("end_location обязателен если смена завершена и есть start_location")

 
        if (self.start_location_lat is None) != (self.start_location_lon is None):
            raise ValueError("start_location_lat и start_location_lon должны быть указаны вместе")

        if (self.end_location_lat is None) != (self.end_location_lon is None):
            raise ValueError("end_location_lat и end_location_lon должны быть указаны вместе")

        if self.early_end_reason and not self.ended_at:
            raise ValueError("early_end_reason может быть указан только для завершённых смен")

        return self

class CourierShiftCreate(BaseSchema):
    courier_id: UUID
    started_at: datetime
    start_location_lat: Optional[float] = Field(None, ge=-90.0, le=90.0)
    start_location_lon: Optional[float] = Field(None, ge=-180.0, le=180.0)
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_location_pair(self):
        if (self.start_location_lat is None) != (self.start_location_lon is None):
            raise ValueError("start_location_lat и start_location_lon должны быть указаны вместе")
        return self

class CourierShiftUpdate(BaseSchema):
    ended_at: Optional[datetime] = None
    orders_completed: Optional[int] = Field(None, ge=0, le=1000)
    end_location_lat: Optional[float] = Field(None, ge=-90.0, le=90.0)
    end_location_lon: Optional[float] = Field(None, ge=-180.0, le=180.0)
    total_distance_km: Optional[float] = Field(None, ge=0.0, le=10000.0)
    break_duration_minutes: Optional[int] = Field(None, ge=0, le=1440)
    notes: Optional[str] = None
    early_end_reason: Optional[str] = Field(None, max_length=500)

class CourierShiftResponse(UUIDMixin, TimestampMixin, CourierShiftBase):
    is_active: bool
    duration_hours: Optional[float]
    net_duration_hours: Optional[float]
    average_distance_per_order: Optional[float]
    has_location_data: bool

    @model_validator(mode="before")
    @classmethod
    def calculate_computed_fields(cls, data: Any) -> Any:
        if hasattr(data, "__dict__"):
            model_data = {
                "id": data.id,
                "created_at": data.created_at,
                "updated_at": data.updated_at,
                "courier_id": data.courier_id,
                "started_at": data.started_at,
                "ended_at": data.ended_at,
                "orders_completed": data.orders_completed,
                "start_location_lat": data.start_location_lat,
                "start_location_lon": data.start_location_lon,
                "end_location_lat": data.end_location_lat,
                "end_location_lon": data.end_location_lon,
                "total_distance_km": data.total_distance_km,
                "break_duration_minutes": data.break_duration_minutes,
                "notes": data.notes,
                "early_end_reason": data.early_end_reason,
                "is_active": getattr(data, "is_active", False),
                "duration_hours": getattr(data, "duration_hours", None),
                "net_duration_hours": getattr(data, "net_duration_hours", None),
                "average_distance_per_order": getattr(data, "average_distance_per_order", None),
                "has_location_data": getattr(data, "has_location_data", False),
            }
            data = model_data
        elif isinstance(data, dict):
            started_at = data.get("started_at")
            ended_at = data.get("ended_at")
            orders_completed = data.get("orders_completed", 0)
            break_duration_minutes = data.get("break_duration_minutes", 0)
            total_distance_km = data.get("total_distance_km", 0.0)
            start_location_lat = data.get("start_location_lat")
            start_location_lon = data.get("start_location_lon")

            if "is_active" not in data:
                data["is_active"] = ended_at is None

            if "duration_hours" not in data:
                if started_at:
                    if ended_at:
                        delta = ended_at - started_at
                        data["duration_hours"] = delta.total_seconds() / 3600
                    else:
                        from datetime import datetime, timezone
                        now = datetime.now(timezone.utc)
                        delta = now - started_at
                        data["duration_hours"] = delta.total_seconds() / 3600
                else:
                    data["duration_hours"] = None

            if "net_duration_hours" not in data:
                duration = data.get("duration_hours")
                if duration is not None:
                    data["net_duration_hours"] = duration - (break_duration_minutes / 60)
                else:
                    data["net_duration_hours"] = None

            if "average_distance_per_order" not in data:
                if orders_completed > 0:
                    data["average_distance_per_order"] = float(total_distance_km) / orders_completed
                else:
                    data["average_distance_per_order"] = None

            if "has_location_data" not in data:
                data["has_location_data"] = (
                    start_location_lat is not None
                    and start_location_lon is not None
                )

        return data

class CourierShiftBrief(UUIDMixin, BaseSchema):
    courier_id: UUID
    started_at: datetime
    ended_at: Optional[datetime]
    is_active: bool
    orders_completed: int

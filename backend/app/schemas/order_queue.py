
from typing import Optional, Any
from uuid import UUID
from datetime import datetime

from pydantic import Field, field_validator, model_validator

from app.models.enums import OrderQueueStatus, DeclineReason
from app.schemas.common import BaseSchema, UUIDMixin, TimestampMixin

class OrderQueueBase(BaseSchema):
    order_id: UUID
    courier_id: UUID
    status: OrderQueueStatus = OrderQueueStatus.OFFERED
    priority: int = Field(..., ge=0, le=100)
    distance_km: float = Field(..., ge=0.0, le=1000.0)
    offered_at: datetime
    expires_at: datetime
    responded_at: Optional[datetime] = None
    decline_reason: Optional[DeclineReason] = None

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, v: datetime, info) -> datetime:
        offered_at = info.data.get("offered_at")
        if offered_at and v <= offered_at:
            raise ValueError("expires_at должен быть позже offered_at")
        return v

    @field_validator("responded_at")
    @classmethod
    def validate_responded_at(cls, v: Optional[datetime], info) -> Optional[datetime]:
        if v is None:
            return None
        offered_at = info.data.get("offered_at")
        if offered_at and v < offered_at:
            raise ValueError("responded_at должен быть позже offered_at")
        return v

    @model_validator(mode="after")
    def validate_decline_reason_logic(self):
        if self.status == OrderQueueStatus.DECLINED and not self.decline_reason:
            raise ValueError("decline_reason обязателен когда status = DECLINED")
        if self.status != OrderQueueStatus.DECLINED and self.decline_reason:
            raise ValueError("decline_reason должен быть None когда status != DECLINED")
        return self

class OrderQueueCreate(BaseSchema):
    order_id: UUID
    courier_id: UUID
    priority: int = Field(..., ge=0, le=100)
    distance_km: float = Field(..., ge=0.0, le=1000.0)
    offered_at: datetime
    expires_at: datetime

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, v: datetime, info) -> datetime:
        offered_at = info.data.get("offered_at")
        if offered_at and v <= offered_at:
            raise ValueError("expires_at должен быть позже offered_at")
        return v

class OrderQueueUpdate(BaseSchema):
    status: Optional[OrderQueueStatus] = None
    responded_at: Optional[datetime] = None
    decline_reason: Optional[DeclineReason] = None

    @model_validator(mode="after")
    def validate_decline_reason_logic(self):
        if self.status == OrderQueueStatus.DECLINED and not self.decline_reason:
            raise ValueError("decline_reason обязателен когда status = DECLINED")
        if self.status and self.status != OrderQueueStatus.DECLINED and self.decline_reason:
            raise ValueError("decline_reason должен быть None когда status != DECLINED")
        return self

class OrderQueueResponse(UUIDMixin, TimestampMixin, OrderQueueBase):
    is_expired: bool
    is_active: bool
    is_accepted: bool
    is_declined: bool
    response_time_seconds: Optional[int]
    time_remaining_seconds: int

    @model_validator(mode="before")
    @classmethod
    def calculate_computed_fields(cls, data: Any) -> Any:
        if hasattr(data, "__dict__"):
            model_data = {
                "id": data.id,
                "created_at": data.created_at,
                "updated_at": data.updated_at,
                "order_id": data.order_id,
                "courier_id": data.courier_id,
                "status": data.status,
                "priority": data.priority,
                "distance_km": data.distance_km,
                "offered_at": data.offered_at,
                "expires_at": data.expires_at,
                "responded_at": data.responded_at,
                "decline_reason": data.decline_reason,
                "is_expired": getattr(data, "is_expired", False),
                "is_active": getattr(data, "is_active", False),
                "is_accepted": getattr(data, "is_accepted", False),
                "is_declined": getattr(data, "is_declined", False),
                "response_time_seconds": getattr(data, "response_time_seconds", None),
                "time_remaining_seconds": getattr(data, "time_remaining_seconds", 0),
            }
            data = model_data
        elif isinstance(data, dict):
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc)
            offered_at = data.get("offered_at")
            expires_at = data.get("expires_at")
            responded_at = data.get("responded_at")
            status = data.get("status")

            if "is_expired" not in data:
                data["is_expired"] = now > expires_at if expires_at else False

            if "is_active" not in data:
                data["is_active"] = (
                    status == OrderQueueStatus.OFFERED and not data["is_expired"]
                )

            if "is_accepted" not in data:
                data["is_accepted"] = status == OrderQueueStatus.ACCEPTED

            if "is_declined" not in data:
                data["is_declined"] = status == OrderQueueStatus.DECLINED

            if "response_time_seconds" not in data:
                if responded_at and offered_at:
                    delta = responded_at - offered_at
                    data["response_time_seconds"] = int(delta.total_seconds())
                else:
                    data["response_time_seconds"] = None

            if "time_remaining_seconds" not in data:
                if expires_at:
                    if now >= expires_at:
                        data["time_remaining_seconds"] = 0
                    else:
                        delta = expires_at - now
                        data["time_remaining_seconds"] = int(delta.total_seconds())
                else:
                    data["time_remaining_seconds"] = 0

        return data

class OrderQueueBrief(UUIDMixin, BaseSchema):
    order_id: UUID
    courier_id: UUID
    status: OrderQueueStatus
    priority: int
    distance_km: float
    expires_at: datetime
    is_expired: bool
    is_active: bool

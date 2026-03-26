
from typing import Optional, Any
from uuid import UUID
from datetime import datetime

from pydantic import Field, field_validator, model_validator

from app.models.enums import SubscriptionTier
from app.schemas.common import BaseSchema, UUIDMixin, TimestampMixin, SoftDeleteMixin

class SubscriptionBase(BaseSchema):
    user_id: UUID
    tier: SubscriptionTier = SubscriptionTier.FREE
    start_date: datetime
    end_date: datetime
    renewed_count: int = Field(default=0, ge=0)
    is_active: bool = True

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, v: datetime, info) -> datetime:
        start_date = info.data.get("start_date")
        if start_date and v <= start_date:
            raise ValueError("end_date должен быть позже start_date")
        return v

class SubscriptionCreate(BaseSchema):
    user_id: UUID
    tier: SubscriptionTier = SubscriptionTier.FREE
    start_date: datetime
    end_date: datetime

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, v: datetime, info) -> datetime:
        start_date = info.data.get("start_date")
        if start_date and v <= start_date:
            raise ValueError("end_date должен быть позже start_date")
        return v

class SubscriptionUpdate(BaseSchema):
    tier: Optional[SubscriptionTier] = None
    end_date: Optional[datetime] = None
    renewed_count: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None

class SubscriptionResponse(UUIDMixin, TimestampMixin, SoftDeleteMixin, SubscriptionBase):
    is_expired: bool
    is_valid: bool
    discount_percentage: float
    days_remaining: int
    is_expiring_soon: bool

    @model_validator(mode="before")
    @classmethod
    def calculate_computed_fields(cls, data: Any) -> Any:
        if hasattr(data, "__dict__"):
            model_data = {
                "id": data.id,
                "created_at": data.created_at,
                "updated_at": data.updated_at,
                "deleted_at": data.deleted_at,
                "user_id": data.user_id,
                "tier": data.tier,
                "start_date": data.start_date,
                "end_date": data.end_date,
                "renewed_count": data.renewed_count,
                "is_active": data.is_active,
                "is_expired": getattr(data, "is_expired", False),
                "is_valid": getattr(data, "is_valid", False),
                "discount_percentage": getattr(data, "discount_percentage", 0.0),
                "days_remaining": getattr(data, "days_remaining", 0),
                "is_expiring_soon": getattr(data, "is_expiring_soon", False),
            }
            data = model_data
        elif isinstance(data, dict):
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc)
            end_date = data.get("end_date")
            is_active = data.get("is_active", True)
            tier = data.get("tier", SubscriptionTier.FREE)

            if "is_expired" not in data:
                data["is_expired"] = now > end_date if end_date else False

            if "is_valid" not in data:
                data["is_valid"] = is_active and not data["is_expired"]

            if "discount_percentage" not in data:
                if data["is_valid"]:
                    discount_map = {
                        SubscriptionTier.FREE: 0.0,
                        SubscriptionTier.BASIC: 20.0,
                        SubscriptionTier.PREMIUM: 30.0,
                    }
                    data["discount_percentage"] = discount_map.get(tier, 0.0)
                else:
                    data["discount_percentage"] = 0.0

            if "days_remaining" not in data:
                if data["is_expired"]:
                    data["days_remaining"] = 0
                elif end_date:
                    delta = end_date - now
                    data["days_remaining"] = max(0, delta.days)
                else:
                    data["days_remaining"] = 0

            if "is_expiring_soon" not in data:
                data["is_expiring_soon"] = 0 < data["days_remaining"] <= 7

        return data

class SubscriptionBrief(UUIDMixin, BaseSchema):
    user_id: UUID
    tier: SubscriptionTier
    end_date: datetime
    is_valid: bool
    discount_percentage: float

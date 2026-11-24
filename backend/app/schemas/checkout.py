from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.models.enums import PaymentStatus, PaymentType, SubscriptionTier
from pydantic import BaseModel, ConfigDict, Field


class CheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    payment_type: PaymentType
    amount: Decimal = Field(gt=0, le=999999.99, max_digits=8, decimal_places=2)
    order_id: UUID | None = None
    subscription_tier: SubscriptionTier | None = None
    duration_months: int | None = Field(None, ge=1, le=12)
    save_payment_method: bool = False


class CheckoutResponse(BaseModel):
    payment_id: UUID
    payment_url: str | None
    amount: float
    status: PaymentStatus
    creation_state: str
    expires_at: datetime | None

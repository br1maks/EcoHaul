
from typing import Optional, Any
from uuid import UUID
from datetime import datetime

from pydantic import Field, field_validator, model_validator

from app.models.enums import PaymentType, PaymentMethod, PaymentStatus
from app.schemas.common import BaseSchema, UUIDMixin, TimestampMixin

class PaymentBase(BaseSchema):
    user_id: UUID
    order_id: Optional[UUID] = None
    subscription_id: Optional[UUID] = None
    refund_for_payment_id: Optional[UUID] = None
    payment_type: PaymentType
    payment_method: PaymentMethod
    amount: float = Field(..., gt=0.0, le=999999.99)
    status: PaymentStatus = PaymentStatus.PENDING
    yookassa_payment_id: Optional[str] = Field(None, max_length=100)
    yookassa_response: Optional[str] = None
    error_message: Optional[str] = Field(None, max_length=500)
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_payment_links(self):
        if self.payment_type == PaymentType.ORDER_PAYMENT:
            if not self.order_id:
                raise ValueError("order_id обязателен для ORDER_PAYMENT")
        
        elif self.payment_type == PaymentType.SUBSCRIPTION_PURCHASE:
            if self.status == PaymentStatus.COMPLETED and not self.subscription_id:
                raise ValueError("subscription_id обязателен для SUBSCRIPTION_PURCHASE")
        elif self.payment_type == PaymentType.REFUND:
            if not self.refund_for_payment_id:
                raise ValueError("refund_for_payment_id обязателен для REFUND")
        return self 
    
class PaymentCreate(BaseSchema):
    user_id: UUID
    order_id: Optional[UUID] = None
    subscription_id: Optional[UUID] = None
    payment_type: PaymentType
    payment_method: PaymentMethod
    amount: float = Field(..., gt=0.0, le=999999.99)

    @model_validator(mode="after")
    def validate_payment_links(self):
        if self.payment_type == PaymentType.ORDER_PAYMENT:
            if not self.order_id:
                raise ValueError("order_id обязателен для ORDER_PAYMENT")
        elif self.payment_type == PaymentType.SUBSCRIPTION_PURCHASE:
            if not self.subscription_id:
                raise ValueError("subscription_id обязателен для SUBSCRIPTION_PURCHASE")
        return self

class PaymentUpdate(BaseSchema):
    status: Optional[PaymentStatus] = None
    yookassa_payment_id: Optional[str] = Field(None, max_length=100)
    yookassa_response: Optional[str] = None
    error_message: Optional[str] = Field(None, max_length=500)
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

class PaymentResponse(UUIDMixin, TimestampMixin, PaymentBase):
    creation_state: str = "LEGACY"
    confirmation_url: Optional[str] = None
    is_pending: bool
    is_completed: bool
    is_failed: bool
    is_cancelled: bool
    is_finalized: bool
    used_wallet: bool
    used_card: bool
    processing_time_seconds: Optional[int]

    @model_validator(mode="before")
    @classmethod
    def calculate_computed_fields(cls, data: Any) -> Any:
        if hasattr(data, "__dict__"):
            model_data = {
                "id": data.id,
                "creation_state": data.creation_state,
                "confirmation_url": data.confirmation_url,
                "created_at": data.created_at,
                "updated_at": data.updated_at,
                "user_id": data.user_id,
                "order_id": data.order_id,
                "subscription_id": data.subscription_id,
                "refund_for_payment_id": data.refund_for_payment_id,
                "payment_type": data.payment_type,
                "payment_method": data.payment_method,
                "amount": data.amount,
                "status": data.status,
                "yookassa_payment_id": data.yookassa_payment_id,
                "yookassa_response": data.yookassa_response,
                "error_message": data.error_message,
                "completed_at": data.completed_at,
                "failed_at": data.failed_at,
                "cancelled_at": data.cancelled_at,
                "is_pending": getattr(data, "is_pending", False),
                "is_completed": getattr(data, "is_completed", False),
                "is_failed": getattr(data, "is_failed", False),
                "is_cancelled": getattr(data, "is_cancelled", False),
                "is_finalized": getattr(data, "is_finalized", False),
                "used_wallet": getattr(data, "used_wallet", False),
                "used_card": getattr(data, "used_card", False),
                "processing_time_seconds": getattr(data, "processing_time_seconds", None),
            }
            data = model_data
        elif isinstance(data, dict):
            status = data.get("status", PaymentStatus.PENDING)
            payment_method = data.get("payment_method")
            created_at = data.get("created_at")
            completed_at = data.get("completed_at")

            if "is_pending" not in data:
                data["is_pending"] = status == PaymentStatus.PENDING
            if "is_completed" not in data:
                data["is_completed"] = status == PaymentStatus.COMPLETED
            if "is_failed" not in data:
                data["is_failed"] = status == PaymentStatus.FAILED
            if "is_cancelled" not in data:
                data["is_cancelled"] = status == PaymentStatus.CANCELLED
            if "is_finalized" not in data:
                data["is_finalized"] = status in [
                    PaymentStatus.COMPLETED,
                    PaymentStatus.FAILED,
                    PaymentStatus.CANCELLED,
                ]
            if "used_wallet" not in data:
                data["used_wallet"] = False  # Wallet support was removed; retain response compatibility.
            if "used_card" not in data:
                data["used_card"] = payment_method == PaymentMethod.CARD
            if "processing_time_seconds" not in data:
                if completed_at and created_at:
                    delta = completed_at - created_at
                    data["processing_time_seconds"] = int(delta.total_seconds())
                else:
                    data["processing_time_seconds"] = None

        return data

class PaymentBrief(UUIDMixin, BaseSchema):
    payment_type: PaymentType
    payment_method: PaymentMethod
    amount: float
    status: PaymentStatus
    created_at: datetime

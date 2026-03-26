
from typing import Optional, Any
from uuid import UUID
from datetime import datetime

from pydantic import Field, field_validator, model_validator

from app.models.enums import UserRole
from app.schemas.common import BaseSchema, UUIDMixin, TimestampMixin

class ReviewBase(BaseSchema):
    reviewer_id: UUID
    reviewee_id: UUID
    order_id: UUID
    moderated_by_id: Optional[UUID] = None
    reviewer_role: UserRole
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None
    response: Optional[str] = None
    is_visible: bool = True
    is_anonymous: bool = False
    moderation_note: Optional[str] = None
    moderated_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None

    @field_validator("reviewer_role")
    @classmethod
    def validate_reviewer_role(cls, v: UserRole) -> UserRole:
        if v not in [UserRole.CLIENT, UserRole.COURIER]:
            raise ValueError("reviewer_role должен быть CLIENT или COURIER")
        return v

    @model_validator(mode="after")
    def validate_review_logic(self):
        if self.reviewer_id == self.reviewee_id:
            raise ValueError("reviewer_id и reviewee_id должны быть разными")

        if self.moderated_at and not self.moderated_by_id:
            raise ValueError("moderated_by_id обязателен если указан moderated_at")

        if self.response and not self.responded_at:
            raise ValueError("responded_at обязателен если указан response")

        return self

class ReviewCreate(BaseSchema):
    reviewee_id: UUID
    order_id: UUID
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None
    is_anonymous: bool = False

class ReviewUpdate(BaseSchema):
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None
    response: Optional[str] = None
    is_visible: Optional[bool] = None
    is_anonymous: Optional[bool] = None
    moderation_note: Optional[str] = None
    moderated_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    moderated_by_id: Optional[UUID] = None

class ReviewResponse(UUIDMixin, TimestampMixin, ReviewBase):
    is_positive: bool
    is_neutral: bool
    is_negative: bool
    has_comment: bool
    has_response: bool
    is_client_review: bool
    is_courier_review: bool
    is_moderated: bool

    @model_validator(mode="before")
    @classmethod
    def calculate_computed_fields(cls, data: Any) -> Any:
        if hasattr(data, "__dict__"):
            model_data = {
                "id": data.id,
                "created_at": data.created_at,
                "updated_at": data.updated_at,
                "reviewer_id": data.reviewer_id,
                "reviewee_id": data.reviewee_id,
                "order_id": data.order_id,
                "moderated_by_id": data.moderated_by_id,
                "reviewer_role": data.reviewer_role,
                "rating": data.rating,
                "comment": data.comment,
                "response": data.response,
                "is_visible": data.is_visible,
                "is_anonymous": data.is_anonymous,
                "moderation_note": data.moderation_note,
                "moderated_at": data.moderated_at,
                "responded_at": data.responded_at,
                "is_positive": getattr(data, "is_positive", False),
                "is_neutral": getattr(data, "is_neutral", False),
                "is_negative": getattr(data, "is_negative", False),
                "has_comment": getattr(data, "has_comment", False),
                "has_response": getattr(data, "has_response", False),
                "is_client_review": getattr(data, "is_client_review", False),
                "is_courier_review": getattr(data, "is_courier_review", False),
                "is_moderated": getattr(data, "is_moderated", False),
            }
            data = model_data
        elif isinstance(data, dict):
            rating = data.get("rating", 3)
            reviewer_role = data.get("reviewer_role")
            comment = data.get("comment")
            response = data.get("response")
            moderated_at = data.get("moderated_at")

            if "is_positive" not in data:
                data["is_positive"] = rating >= 4

            if "is_neutral" not in data:
                data["is_neutral"] = rating == 3

            if "is_negative" not in data:
                data["is_negative"] = rating <= 2

            if "has_comment" not in data:
                data["has_comment"] = comment is not None and len(str(comment).strip()) > 0

            if "has_response" not in data:
                data["has_response"] = response is not None and len(str(response).strip()) > 0

            if "is_client_review" not in data:
                data["is_client_review"] = reviewer_role == UserRole.CLIENT

            if "is_courier_review" not in data:
                data["is_courier_review"] = reviewer_role == UserRole.COURIER

            if "is_moderated" not in data:
                data["is_moderated"] = moderated_at is not None

        return data

class ReviewBrief(UUIDMixin, BaseSchema):
    reviewer_role: UserRole
    rating: int
    is_anonymous: bool
    has_comment: bool
    created_at: datetime

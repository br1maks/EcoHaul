from typing import Optional
from .base import TimestampMixin, Base, IDMixin
from uuid import UUID
from datetime import datetime 

from sqlalchemy import String, Boolean, Integer, ForeignKey, DateTime, Index, Text, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .enums import UserRole

class Review(Base, IDMixin, TimestampMixin):
    __tablename__ = "reviews"

    reviewer_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False,
    )

    reviewee_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )

    moderated_by_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    reviewer_role: Mapped[UserRole] = mapped_column(
        String(10),
        nullable=False,
    )

    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    comment: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    response: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    is_visible: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    is_anonymous: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    moderation_note: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    moderated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    responded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    reviewer = relationship(
        "User",
        foreign_keys=[reviewer_id],
        back_populates="reviews_given",
    )

    reviewee = relationship(
        "User",
        foreign_keys=[reviewee_id],
        back_populates="reviews_received",
    )

    order = relationship(
        "Order",
        back_populates="reviews",
    )

    moderator = relationship(
        "User",
        foreign_keys=[moderated_by_id],
    )

    __table_args__ = (
        UniqueConstraint("order_id", "reviewer_id", name="uq_order_reviewer"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="check_rating_range"),
        Index("idx_review_order_id", "order_id"),
        Index("idx_review_reviewer_id", "reviewer_id"),
        Index("idx_review_reviewee_id", "reviewee_id"),
        Index("idx_review_is_visible", "is_visible"),
        Index("idx_review_rating", "rating"),
        Index("idx_review_reviewer_role", "reviewer_role"),
        Index("idx_review_reviewee_visible", "reviewee_id", "is_visible"),
        Index("idx_review_reviewee_rating", "reviewee_id", "rating"),
        Index("idx_review_moderated_by", "moderated_by_id"),
    )

    @property
    def is_positive(self) -> bool:
        return self.rating >= 4

    @property
    def is_neutral(self) -> bool:
        return self.rating == 3

    @property
    def is_negative(self) -> bool:
        return self.rating <= 2
    
    @property
    def has_comment(self) -> bool:
        return self.comment is not None and len(self.comment.strip()) > 0
    
    @property
    def has_response(self) -> bool:
        return self.response is not None and len(self.response.strip()) > 0

    @property
    def is_client_review(self) -> bool:
        return self.reviewer_role == UserRole.CLIENT

    @property
    def is_courier_review(self) -> bool:
        return self.reviewer_role == UserRole.COURIER

    @property
    def is_moderated(self) -> bool:
        return self.moderated_at is not None
    
    def __repr__(self) -> str:
        return (
            f"<Review(id={self.id}, reviewer_role={self.reviewer_role}, "
            f"rating={self.rating}, order_id={self.order_id})>"
        )
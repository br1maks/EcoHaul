
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.dependencies import get_current_active_user, require_admin
from app.models.user import User
from app.models.order import Order
from app.models.review import Review
from app.models.enums import OrderStatus, UserRole
from app.schemas.review import ReviewCreate, ReviewUpdate, ReviewResponse

router = APIRouter(prefix="/reviews", tags=["Отзывы"])

async def recalculate_courier_rating(courier_id: UUID, db: AsyncSession) -> None:
    stmt = select(User).where(User.id == courier_id)
    result = await db.execute(stmt)
    courier = result.scalar_one_or_none()

    if not courier:
        return

    stmt = select(func.avg(Review.rating)).where(
        Review.reviewee_id == courier_id,
        Review.is_visible == True
    )
    result = await db.execute(stmt)
    avg_rating = result.scalar()

    if avg_rating is None:
        avg_rating = 5.0

    courier.rating = round(float(avg_rating), 2)

    await db.flush()

@router.post("", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    review_data: ReviewCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):

    stmt = select(Order).where(Order.id == review_data.order_id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заказ не найден"
        )

    order_status = order.status if isinstance(order.status, str) else order.status.value
    if order_status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Можно оставить отзыв только на завершённый заказ"
        )

    if order.client_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы можете оставить отзыв только на свой заказ"
        )

    if review_data.reviewee_id != order.courier_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Отзыв должен быть оставлен курьеру, который выполнил заказ"
        )

    stmt = select(Review).where(
        Review.order_id == review_data.order_id,
        Review.reviewer_id == current_user.id
    )
    result = await db.execute(stmt)
    existing_review = result.scalar_one_or_none()

    if existing_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Вы уже оставили отзыв на этот заказ"
        )

    review = Review(
        reviewer_id=current_user.id,
        reviewee_id=review_data.reviewee_id,
        order_id=review_data.order_id,
        reviewer_role=current_user.role,
        rating=review_data.rating,
        comment=review_data.comment,
        is_anonymous=review_data.is_anonymous,
    )

    db.add(review)
    await db.flush()

    await recalculate_courier_rating(review_data.reviewee_id, db)

    await db.commit()
    await db.refresh(review)

    return review

@router.get("/my-reviews", response_model=list[ReviewResponse])
async def get_my_reviews(
    limit: int = Query(20, ge=1, le=100, description="Количество отзывов"),
    offset: int = Query(0, ge=0, description="Смещение"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):

    stmt = (
        select(Review)
        .where(Review.reviewer_id == current_user.id)
        .order_by(Review.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    reviews = result.scalars().all()

    return reviews

@router.get("/about-me", response_model=list[ReviewResponse])
async def get_reviews_about_me(
    limit: int = Query(20, ge=1, le=100, description="Количество отзывов"),
    offset: int = Query(0, ge=0, description="Смещение"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Review)
        .where(Review.reviewee_id == current_user.id)
        .order_by(Review.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    reviews = result.scalars().all()

    return reviews

@router.get("/courier/{courier_id}", response_model=list[ReviewResponse])
async def get_courier_reviews(
    courier_id: UUID,
    limit: int = Query(20, ge=1, le=100, description="Количество отзывов"),
    offset: int = Query(0, ge=0, description="Смещение"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).where(User.id == courier_id)
    result = await db.execute(stmt)
    courier = result.scalar_one_or_none()

    if not courier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Курьер не найден"
        )

    stmt = (
        select(Review)
        .where(
            Review.reviewee_id == courier_id,
            Review.is_visible == True
        )
        .order_by(Review.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    reviews = result.scalars().all()

    return reviews

@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Review).where(Review.id == review_id)
    result = await db.execute(stmt)
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отзыв не найден"
        )

    is_author = review.reviewer_id == current_user.id
    is_reviewee = review.reviewee_id == current_user.id
    is_admin = current_user.role == UserRole.ADMIN

    if not (is_author or is_reviewee or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этому отзыву"
        )

    return review

@router.patch("/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: UUID,
    review_data: ReviewUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Review).where(Review.id == review_id)
    result = await db.execute(stmt)
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отзыв не найден"
        )

    is_author = review.reviewer_id == current_user.id
    is_reviewee = review.reviewee_id == current_user.id
    is_admin = current_user.role == UserRole.ADMIN

    if not (is_author or is_reviewee or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этому отзыву"
        )

    rating_changed = False

    if is_author and not is_reviewee:
        if review_data.rating is not None:
            if review.rating != review_data.rating:
                rating_changed = True
            review.rating = review_data.rating
        if review_data.comment is not None:
            review.comment = review_data.comment
        if review_data.is_anonymous is not None:
            review.is_anonymous = review_data.is_anonymous

    if is_reviewee and not is_author:
        if review_data.response is not None:
            review.response = review_data.response
            review.responded_at = datetime.now(timezone.utc)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Вы можете только добавить ответ на отзыв"
            )

    if is_admin:
        if review_data.is_visible is not None:
            review.is_visible = review_data.is_visible
        if review_data.moderation_note is not None:
            review.moderation_note = review_data.moderation_note
            review.moderated_at = datetime.now(timezone.utc)
            review.moderated_by_id = current_user.id
        if review_data.rating is not None:
            if review.rating != review_data.rating:
                rating_changed = True
            review.rating = review_data.rating
        if review_data.comment is not None:
            review.comment = review_data.comment
        if review_data.response is not None:
            review.response = review_data.response

    if rating_changed:
        await recalculate_courier_rating(review.reviewee_id, db)

    await db.commit()
    await db.refresh(review)

    return review

@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    review_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Review).where(Review.id == review_id)
    result = await db.execute(stmt)
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отзыв не найден"
        )

    is_author = review.reviewer_id == current_user.id
    is_admin = current_user.role == UserRole.ADMIN

    if not (is_author or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к удалению этого отзыва"
        )

    reviewee_id = review.reviewee_id

    await db.delete(review)

    await recalculate_courier_rating(reviewee_id, db)

    await db.commit()

    return None

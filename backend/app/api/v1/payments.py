
import logging
import asyncio
from decimal import Decimal
from typing import Optional, Any, cast
from uuid import UUID
from datetime import datetime, timedelta, timezone
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.payment import Payment
from app.models.subscription import Subscription
from app.models.order import Order
from app.models.enums import (
    PaymentType,
    PaymentMethod,
    PaymentStatus,
    SubscriptionTier
)
from app.schemas.payment import PaymentResponse, PaymentCreate
from app.services.yookassa_service import YooKassaService

logger = logging.getLogger(__name__)

class PaymentCreateRequest(BaseModel):
    payment_type: PaymentType = Field(..., description="Тип платежа")
    amount: float = Field(..., gt=0.0, le=999999.99, description="Сумма платежа")
    order_id: Optional[UUID] = Field(None, description="ID заказа (для ORDER_PAYMENT)")
    subscription_tier: Optional[SubscriptionTier] = Field(None, description="Тариф подписки (для SUBSCRIPTION_PURCHASE)")
    duration_months: Optional[int] = Field(None, ge=1, le=12, description="Длительность подписки в месяцах")
    save_payment_method: bool = Field(False, description="Сохранить способ оплаты для автопродления")

class PaymentCreateResponse(BaseModel):
    payment_id: UUID
    payment_url: str
    amount: float
    expires_at: datetime

class PaymentListResponse(BaseModel):
    items: list[PaymentResponse]
    total: int
    page: int
    size: int
    pages: int

router = APIRouter(prefix="/payments", tags=["Платежи"])

@router.post("", response_model=PaymentCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    data: PaymentCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    logger.info(
        f"Creating payment: user_id={current_user.id}, "
        f"type={data.payment_type.value}, amount={data.amount} BYN, "
        f"order_id={data.order_id}"
    )

    if data.payment_type == PaymentType.ORDER_PAYMENT:
        if not data.order_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="order_id обязателен для ORDER_PAYMENT"
            )

        stmt = select(Order).where(
            and_(
                Order.id == data.order_id,
                Order.client_id == current_user.id
            )
        )
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Заказ не найден"
            )

    elif data.payment_type == PaymentType.SUBSCRIPTION_PURCHASE:
        if not data.subscription_tier or data.subscription_tier == SubscriptionTier.FREE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Тариф подписки должен быть BASIC или PREMIUM"
            )

    else:
        raise HTTPException(status_code=400, detail="Этот тип платежа нельзя создать через checkout")

    if data.payment_type == PaymentType.ORDER_PAYMENT:
        expected_amount = Decimal(str(order.final_price))
    else:
        if not data.duration_months:
            raise HTTPException(status_code=400, detail="Укажите длительность подписки")
        prices = {SubscriptionTier.BASIC: Decimal("5.00"), SubscriptionTier.PREMIUM: Decimal("10.00")}
        expected_amount = prices[data.subscription_tier] * data.duration_months
    if Decimal(str(data.amount)) != expected_amount:
        raise HTTPException(status_code=400, detail="Сумма платежа не соответствует стоимости")

    payment = Payment(
        user_id=current_user.id,
        order_id=data.order_id,
        payment_type=data.payment_type,
        payment_method=PaymentMethod.CARD,
        amount=data.amount,
        status=PaymentStatus.PENDING,
    )

    db.add(payment)
    await db.flush()

    if data.payment_type == PaymentType.ORDER_PAYMENT:
        description = f"Оплата заказа #{data.order_id}"
    elif data.subscription_tier and data.duration_months:
        description = f"Подписка {data.subscription_tier.value} на {data.duration_months} мес."
    else:
        description = "Оплата"

    return_url = settings.yookassa_return_url_computed

    metadata = {
        "payment_id": str(payment.id),
        "user_id": str(current_user.id),
        "payment_type": data.payment_type.value,
    }

    if data.subscription_tier:
        metadata["tier"] = data.subscription_tier.value
    if data.duration_months:
        metadata["duration_months"] = str(data.duration_months)

    try:
        logger.info(f"Calling YooKassa API: amount={data.amount}, save_method={data.save_payment_method}")

        yk_payment_obj: Any = await asyncio.to_thread(YooKassaService.create_payment,
            amount=data.amount,
            description=description,
            return_url=return_url,
            save_payment_method=data.save_payment_method,
            metadata=metadata
        )

        payment.yookassa_payment_id = str(yk_payment_obj.id)
        logger.info(f"YooKassa payment created: yk_payment_id={payment.yookassa_payment_id}, payment_id={payment.id}")

        try:
            yk_dict = yk_payment_obj.__dict__ if hasattr(yk_payment_obj, '__dict__') else {}
            payment.yookassa_response = json.dumps(yk_dict, default=str)
        except (TypeError, AttributeError):
            payment.yookassa_response = str(yk_payment_obj)

        if not hasattr(yk_payment_obj, 'confirmation') or not hasattr(yk_payment_obj.confirmation, 'confirmation_url'):
            payment.status = PaymentStatus.FAILED
            payment.error_message = "ЮKassa не вернул confirmation_url"
            payment.failed_at = datetime.now(timezone.utc)
            await db.commit()
            raise ValueError("ЮKassa не вернул confirmation_url")

        payment_url = str(yk_payment_obj.confirmation.confirmation_url)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

        await db.commit()

        logger.info(
            f"Payment created successfully: payment_id={payment.id}, "
            f"url={payment_url}, expires={expires_at}"
        )

        return PaymentCreateResponse(
            payment_id=payment.id,
            payment_url=payment_url,
            amount=data.amount,
            expires_at=expires_at
        )

    except Exception as e:
        await db.rollback()
        payment.status = PaymentStatus.FAILED
        payment.error_message = str(e)
        payment.failed_at = datetime.now(timezone.utc)
        await db.commit()

        logger.error(
            f"Payment creation failed: payment_id={payment.id}, "
            f"user_id={current_user.id}, error={str(e)}",
            exc_info=True
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось создать платёж. Попробуйте позже."
        )

@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Payment).where(
        Payment.id == payment_id,
        Payment.user_id == current_user.id
    )
    result = await db.execute(stmt)
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Платёж не найден"
        )

    return payment

@router.get("", response_model=PaymentListResponse)
async def get_my_payments(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    payment_type: Optional[PaymentType] = Query(None, description="Фильтр по типу платежа"),
    status_filter: Optional[PaymentStatus] = Query(None, description="Фильтр по статусу"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    filters = [Payment.user_id == current_user.id]

    if payment_type:
        filters.append(Payment.payment_type == payment_type)
    if status_filter:
        filters.append(Payment.status == status_filter)

    count_stmt = select(func.count()).select_from(Payment).where(and_(*filters))
    total = await db.scalar(count_stmt) or 0

    offset = (page - 1) * size
    stmt = (
        select(Payment)
        .where(and_(*filters))
        .order_by(Payment.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    result = await db.execute(stmt)
    payments = result.scalars().all()

    pages = (total + size - 1) // size

    return PaymentListResponse(
        items=[PaymentResponse.model_validate(p) for p in payments],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )

@router.post("/yookassa/webhook", status_code=status.HTTP_200_OK)
async def yookassa_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        body = await request.json()
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid JSON")
    if not isinstance(body, dict) or not isinstance(body.get("object"), dict):
        raise HTTPException(status_code=400, detail="Invalid notification")

    event_type = body.get("event")
    if not isinstance(event_type, str):
        raise HTTPException(status_code=400, detail="Invalid event type")
    payment_data = body.get("object")

    logger.info(f"Webhook event: {event_type}, payment_id={payment_data.get('id') if payment_data else 'N/A'}")

    if not payment_data:
        logger.error("Webhook: no payment data in body")
        return {"status": "error", "message": "No payment data"}

    yookassa_payment_id = payment_data.get("id")
    if not isinstance(yookassa_payment_id, str) or not yookassa_payment_id:
        raise HTTPException(status_code=400, detail="Missing payment id")
    expected_status = {"payment.succeeded": "succeeded", "payment.canceled": "canceled"}.get(event_type)
    if expected_status is None:
        return {"status": "event_not_handled"}
    # YooKassa does not sign notifications using X-Webhook-Signature.
    # Fetch the current object through the authenticated provider API instead.
    try:
        remote = await asyncio.to_thread(YooKassaService.get_payment_info, yookassa_payment_id)
    except Exception:
        logger.exception("Could not verify payment notification with provider")
        raise HTTPException(status_code=502, detail="Payment verification unavailable")
    if remote.id != yookassa_payment_id or remote.status != expected_status:
        raise HTTPException(status_code=409, detail="Provider status does not match notification")
    payment_data = {
        "id": remote.id, "status": remote.status,
        "metadata": dict(remote.metadata or {}),
        "payment_method": {"saved": bool(getattr(remote.payment_method, "saved", False)),
                           "id": getattr(remote.payment_method, "id", None)},
    }
    stmt = select(Payment).where(Payment.yookassa_payment_id == yookassa_payment_id).with_for_update(of=Payment)
    result = await db.execute(stmt)
    payment = result.scalar_one_or_none()

    if not payment:
        logger.warning(f"Webhook: payment not found for yk_id={yookassa_payment_id}")
        return {"status": "payment_not_found"}

    if (Decimal(str(remote.amount.value)) != Decimal(str(payment.amount))
            or remote.amount.currency != "BYN"
            or payment_data["metadata"].get("payment_id") != str(payment.id)
            or payment_data["metadata"].get("user_id") != str(payment.user_id)):
        raise HTTPException(status_code=409, detail="Provider payment does not match local record")

    if payment.status != PaymentStatus.PENDING:
        logger.info(f"Webhook: payment {payment.id} already processed (status={payment.status})")
        return {"status": "already_processed"}

    if event_type == "payment.succeeded":
        logger.info(f"Webhook: payment.succeeded for payment_id={payment.id}")

        payment.status = PaymentStatus.COMPLETED
        payment.completed_at = datetime.now(timezone.utc)
        payment.yookassa_response = json.dumps(payment_data, default=str)

        if payment.payment_type == PaymentType.SUBSCRIPTION_PURCHASE:
            logger.info(f"Webhook: processing subscription purchase for payment_id={payment.id}")
            await db.execute(select(User).where(User.id == payment.user_id).with_for_update(of=User))
            metadata = payment_data.get("metadata", {})
            tier_str = metadata.get("tier")
            duration_months = int(metadata.get("duration_months", 1))

            if tier_str:
                tier = SubscriptionTier(tier_str)

                old_sub_stmt = select(Subscription).where(
                    Subscription.user_id == payment.user_id,
                    Subscription.is_active == True
                )
                result = await db.execute(old_sub_stmt)
                old_sub = result.scalar_one_or_none()

                if old_sub:
                    old_sub.is_active = False

                now = datetime.now(timezone.utc)
                end_date = now + timedelta(days=30 * duration_months)

                new_sub = Subscription(
                    user_id=payment.user_id,
                    tier=tier,
                    start_date=now,
                    end_date=end_date,
                    is_active=True,
                    last_payment_id=payment.id
                )

                payment_method_data = payment_data.get("payment_method", {})
                if payment_method_data.get("saved"):
                    payment_method_id = payment_method_data.get("id")
                    new_sub.yookassa_payment_method_id = payment_method_id
                    new_sub.auto_renew_enabled = True
                    new_sub.next_billing_date = end_date

                db.add(new_sub)
                await db.flush()
                payment.subscription_id = new_sub.id

                logger.info(
                    f"Webhook: subscription created: sub_id={new_sub.id}, "
                    f"tier={tier.value}, user_id={payment.user_id}, "
                    f"auto_renew={new_sub.auto_renew_enabled}"
                )

        elif payment.payment_type == PaymentType.ORDER_PAYMENT:
            logger.info(f"Webhook: processing order payment for payment_id={payment.id}")
            # Payment settlement does not alter delivery progress.

        await db.commit()

        logger.info(f"Webhook: payment.succeeded processed successfully for payment_id={payment.id}")
        return {"status": "ok", "event": "payment.succeeded"}

    elif event_type == "payment.canceled":
        logger.info(f"Webhook: payment.canceled for payment_id={payment.id}")

        payment.status = PaymentStatus.CANCELLED
        payment.cancelled_at = datetime.now(timezone.utc)
        payment.yookassa_response = json.dumps(payment_data, default=str)

        await db.commit()

        logger.info(f"Webhook: payment.canceled processed successfully for payment_id={payment.id}")
        return {"status": "ok", "event": "payment.canceled"}

    logger.warning(f"Webhook: unhandled event type: {event_type}")
    return {"status": "event_not_handled", "event": event_type}

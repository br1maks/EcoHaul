
import logging
from typing import Optional, Any
from uuid import UUID
from datetime import datetime, timedelta, timezone
import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.api.dependencies import get_current_active_user, require_admin
from app.models.user import User
from app.models.subscription import Subscription
from app.models.payment import Payment
from app.models.enums import SubscriptionTier, PaymentType, PaymentMethod, PaymentStatus, UserRole
from app.schemas.subscription import SubscriptionResponse
from app.services.yookassa_service import YooKassaService

logger = logging.getLogger(__name__)

class SubscriptionPurchase(BaseModel):
    tier: SubscriptionTier = Field(..., description="Тариф подписки (BASIC или PREMIUM)")
    duration_months: int = Field(1, ge=1, le=12, description="Продолжительность подписки (1-12 месяцев)")

class SubscriptionPurchaseResponse(BaseModel):
    payment_id: UUID
    payment_url: str
    amount: float
    tier: SubscriptionTier
    duration_months: int

class RecurringEnableRequest(BaseModel):
    tier: SubscriptionTier = Field(..., description="Тариф подписки для автопродления")

class SubscriptionPlan(BaseModel):
    tier: SubscriptionTier
    name: str
    description: str
    discount_percentage: float
    price_per_month: float
    features: list[str]

class SubscriptionListResponse(BaseModel):
    items: list[SubscriptionResponse]
    total: int
    page: int
    size: int
    pages: int

class SubscriptionUpdateAdmin(BaseModel):
    tier: Optional[SubscriptionTier] = Field(None, description="Изменить тариф")
    end_date: Optional[datetime] = Field(None, description="Изменить дату окончания")
    is_active: Optional[bool] = Field(None, description="Активировать/деактивировать")

router = APIRouter(prefix="/subscriptions", tags=["Подписки"])

@router.get("/plans", response_model=list[SubscriptionPlan])
async def get_subscription_plans():
    plans = [
        SubscriptionPlan(
            tier=SubscriptionTier.FREE,
            name="Бесплатный",
            description="Базовые возможности сервиса",
            discount_percentage=0.0,
            price_per_month=0.0,
            features=[
                "Вывоз мусора по запросу",
                "Стандартная цена 2 BYN за мешок",
                "История заказов",
            ],
        ),
        SubscriptionPlan(
            tier=SubscriptionTier.BASIC,
            name="Базовый",
            description="Экономьте 20% на каждом заказе",
            discount_percentage=20.0,
            price_per_month=5.0,
            features=[
                "Скидка 20% на все заказы",
                "Приоритетная обработка",
                "История заказов",
                "Уведомления о статусе",
            ],
        ),
        SubscriptionPlan(
            tier=SubscriptionTier.PREMIUM,
            name="Премиум",
            description="Максимальная выгода - скидка 30%",
            discount_percentage=30.0,
            price_per_month=10.0,
            features=[
                "Скидка 30% на все заказы",
                "Наивысший приоритет",
                "Бесплатная отмена заказов",
                "Персональный менеджер",
                "Расширенная статистика",
            ],
        ),
    ]
    return plans

@router.get("/me", response_model=SubscriptionResponse)
async def get_my_subscription(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):

    stmt = select(Subscription).where(
        Subscription.user_id == current_user.id,
        Subscription.is_active == True
    )
    result = await db.execute(stmt)
    subscription = result.scalar_one_or_none()

    if subscription is None:
        now = datetime.now(timezone.utc)
        subscription = Subscription(
            user_id=current_user.id,
            tier=SubscriptionTier.FREE,
            start_date=now,
            end_date=now + timedelta(days=365*100),
            is_active=True,
        )

        db.add(subscription)
        await db.commit()

    return subscription

@router.post("/purchase", response_model=SubscriptionPurchaseResponse, status_code=status.HTTP_201_CREATED)
async def purchase_subscription(
    data: SubscriptionPurchase,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):

    if data.tier == SubscriptionTier.FREE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя купить бесплатную подписку. Выберите BASIC или PREMIUM."
        )

    price_map = {
        SubscriptionTier.BASIC: 5.0,
        SubscriptionTier.PREMIUM: 10.0,
    }

    price_per_month = price_map.get(data.tier, 0.0)
    total_amount = price_per_month * data.duration_months

    payment = Payment(
        user_id=current_user.id,
        payment_type=PaymentType.SUBSCRIPTION_PURCHASE,
        payment_method=PaymentMethod.CARD,
        amount=total_amount,
        status=PaymentStatus.PENDING,
    )

    db.add(payment)
    await db.flush()

    description = f"Подписка {data.tier.value} на {data.duration_months} мес."
    return_url = settings.YOOKASSA_RETURN_URL

    metadata = {
        "payment_id": str(payment.id),
        "user_id": str(current_user.id),
        "payment_type": PaymentType.SUBSCRIPTION_PURCHASE.value,
        "tier": data.tier.value,
        "duration_months": data.duration_months,
    }

    try:
        yk_payment_obj: Any = YooKassaService.create_payment(
            amount=total_amount,
            description=description,
            return_url=return_url,
            save_payment_method=False,
            metadata=metadata
        )

        payment.yookassa_payment_id = str(yk_payment_obj.id)

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

        await db.commit()

        return SubscriptionPurchaseResponse(
            payment_id=payment.id,
            payment_url=payment_url,
            amount=total_amount,
            tier=data.tier,
            duration_months=data.duration_months
        )

    except Exception as e:
        await db.rollback()
        payment.status = PaymentStatus.FAILED
        payment.error_message = str(e)
        payment.failed_at = datetime.now(timezone.utc)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании платежа: {str(e)}"
        )

@router.post("/recurring/enable", response_model=SubscriptionPurchaseResponse, status_code=status.HTTP_201_CREATED)
async def enable_auto_renew(
    data: RecurringEnableRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if data.tier == SubscriptionTier.FREE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя включить автопродление для бесплатной подписки"
        )

    price_map = {
        SubscriptionTier.BASIC: 5.0,
        SubscriptionTier.PREMIUM: 10.0,
    }

    amount = price_map.get(data.tier, 0.0)

    payment = Payment(
        user_id=current_user.id,
        payment_type=PaymentType.SUBSCRIPTION_PURCHASE,
        payment_method=PaymentMethod.CARD,
        amount=amount,
        status=PaymentStatus.PENDING,
    )

    db.add(payment)
    await db.flush()

    description = f"Автопродление подписки {data.tier.value}"
    return_url = settings.YOOKASSA_RETURN_URL

    metadata = {
        "payment_id": str(payment.id),
        "user_id": str(current_user.id),
        "payment_type": PaymentType.SUBSCRIPTION_PURCHASE.value,
        "tier": data.tier.value,
        "duration_months": 1,
    }

    try:
        yk_payment_obj: Any = YooKassaService.create_payment(
            amount=amount,
            description=description,
            return_url=return_url,
            save_payment_method=True,
            metadata=metadata
        )

        payment.yookassa_payment_id = str(yk_payment_obj.id)

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

        await db.commit()

        return SubscriptionPurchaseResponse(
            payment_id=payment.id,
            payment_url=payment_url,
            amount=amount,
            tier=data.tier,
            duration_months=1
        )

    except Exception as e:
        await db.rollback()
        payment.status = PaymentStatus.FAILED
        payment.error_message = str(e)
        payment.failed_at = datetime.now(timezone.utc)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании платежа: {str(e)}"
        )

@router.delete("/recurring/disable", status_code=status.HTTP_200_OK)
async def disable_auto_renew(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Subscription).where(
        Subscription.user_id == current_user.id,
        Subscription.is_active == True
    )
    result = await db.execute(stmt)
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Активная подписка не найдена"
        )

    if not subscription.auto_renew_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Автопродление уже выключено"
        )

    subscription.auto_renew_enabled = False
    subscription.yookassa_payment_method_id = None
    subscription.next_billing_date = None

    await db.commit()

    return {
        "message": "Автопродление успешно отключено",
        "subscription_valid_until": subscription.end_date
    }


import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.api.checkout_response import checkout_response
from app.api.dependencies import get_current_active_user
from app.core.config import settings
from app.core.database import get_db
from app.models.enums import PaymentType, SubscriptionTier
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.checkout import CheckoutRequest, CheckoutResponse
from app.schemas.subscription import SubscriptionResponse
from app.services.payment_lifecycle import PRICES, begin_checkout
from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class SubscriptionPurchase(BaseModel):
    tier: SubscriptionTier = Field(..., description="Тариф подписки (BASIC или PREMIUM)")
    duration_months: int = Field(
        1, ge=1, le=12, description="Продолжительность подписки (1-12 месяцев)"
    )


class RecurringEnableRequest(BaseModel):
    tier: SubscriptionTier = Field(..., description="Тариф подписки для автопродления")


class SubscriptionPlan(BaseModel):
    tier: SubscriptionTier
    name: str
    description: str
    discount_percentage: float
    price_per_month: float
    features: list[str]


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
                f"Стандартная цена {settings.BASE_PRICE_PER_BAG:g} {settings.PAYMENT_CURRENCY} за мешок",
                "История заказов",
            ],
        ),
        SubscriptionPlan(
            tier=SubscriptionTier.BASIC,
            name="Базовый",
            description="Экономьте 20% на каждом заказе",
            discount_percentage=20.0,
            price_per_month=float(PRICES[SubscriptionTier.BASIC]),
            features=[
                "Скидка 20% на все заказы",
                "История заказов",
                "Уведомления о статусе",
            ],
        ),
        SubscriptionPlan(
            tier=SubscriptionTier.PREMIUM,
            name="Премиум",
            description="Максимальная выгода - скидка 30%",
            discount_percentage=30.0,
            price_per_month=float(PRICES[SubscriptionTier.PREMIUM]),
            features=[
                "Скидка 30% на все заказы",
                "История заказов и уведомления о статусе",
            ],
        ),
    ]
    return plans


@router.get("/me", response_model=SubscriptionResponse)
async def get_my_subscription(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(select(User).where(User.id == current_user.id).with_for_update(of=User))
    subscription = await db.scalar(
        select(Subscription).where(Subscription.user_id == current_user.id)
    )
    now = datetime.now(timezone.utc)
    if subscription is None:
        subscription = Subscription(
            user_id=current_user.id,
            tier=SubscriptionTier.FREE,
            start_date=now,
            end_date=now + timedelta(days=36500),
            is_active=True,
        )
        db.add(subscription)
    elif not subscription.is_active or subscription.end_date <= now:
        subscription.tier = SubscriptionTier.FREE
        subscription.start_date, subscription.end_date = now, now + timedelta(days=36500)
        subscription.is_active = True
        subscription.auto_renew_enabled = False
        subscription.next_billing_date = None
    await db.flush()
    await db.refresh(subscription)
    result = SubscriptionResponse.model_validate(subscription)
    await db.commit()
    return result


@router.post(
    "/purchase",
    response_model=CheckoutResponse,
    status_code=201,
    responses={202: {"model": CheckoutResponse, "description": "Pending provider recovery"}},
)
async def purchase_subscription(
    data: SubscriptionPurchase,
    response: Response,
    idempotency_key: UUID = Header(alias="Idempotency-Key"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if data.tier not in PRICES:
        raise HTTPException(status_code=400, detail="Выберите BASIC или PREMIUM")
    request = CheckoutRequest(
        payment_type=PaymentType.SUBSCRIPTION_PURCHASE,
        amount=PRICES[data.tier] * data.duration_months,
        subscription_tier=data.tier,
        duration_months=data.duration_months,
    )
    return checkout_response(
        await begin_checkout(db, current_user.id, request, idempotency_key), response
    )


@router.post("/recurring/enable", status_code=409)
async def enable_auto_renew(
    data: RecurringEnableRequest, current_user: User = Depends(get_current_active_user)
):
    raise HTTPException(
        status_code=409,
        detail="Автоматические списания ещё не поддерживаются. Используйте разовую покупку подписки.",
    )


@router.delete("/recurring/disable", status_code=status.HTTP_200_OK)
async def disable_auto_renew(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Subscription).where(
        Subscription.user_id == current_user.id, Subscription.is_active == True
    )
    result = await db.execute(stmt)
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Активная подписка не найдена"
        )

    if not subscription.auto_renew_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Автопродление уже выключено"
        )

    subscription.auto_renew_enabled = False
    subscription.yookassa_payment_method_id = None
    subscription.next_billing_date = None

    await db.commit()

    return {
        "message": "Автопродление успешно отключено",
        "subscription_valid_until": subscription.end_date,
    }

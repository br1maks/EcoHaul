
import logging
from typing import List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import require_admin
from app.models.user import User
from app.schemas.payment import PaymentResponse
from app.schemas.subscription import SubscriptionResponse
from app.services.payment_monitoring import PaymentMonitoringService
from app.services.payment_lifecycle import recover_payment, accept_provider_state, load_payment, require_payments
from app.services.yookassa_service import YooKassaService
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/payments", tags=["Админ: Платежи"])


class ProviderReference(BaseModel):
    provider_id: str | None = None


@router.post("/{payment_id}/reconcile", response_model=PaymentResponse)
async def reconcile_payment(payment_id: UUID, data: ProviderReference,
                            admin: User = Depends(require_admin)):
    require_payments()
    if data.provider_id:
        if not 1 <= len(data.provider_id) <= 100:
            raise HTTPException(status_code=400, detail="Invalid provider id")
        try:
            async with asyncio.timeout(15):
                remote = await asyncio.to_thread(YooKassaService.get_payment_info, data.provider_id)
        except Exception:
            raise HTTPException(status_code=502, detail="Provider verification unavailable")
        metadata = dict(getattr(remote, "metadata", None) or {})
        if metadata.get("payment_id") != str(payment_id) or remote.id != data.provider_id:
            raise HTTPException(status_code=409, detail="Provider identity does not match requested payment")
        await accept_provider_state(remote)
        return await load_payment(payment_id)
    return await recover_payment(payment_id, force=True)

class PaymentStatisticsResponse(BaseModel):
    period_hours: int
    generated_at: str
    by_status: Dict[str, Dict[str, Any]]
    by_type: Dict[str, Dict[str, Any]]
    success_rate: float

class StuckPaymentsResponse(BaseModel):
    count: int
    payments: List[PaymentResponse]

class FailedPaymentsResponse(BaseModel):
    count: int
    payments: List[PaymentResponse]

class ExpiringSubscriptionsResponse(BaseModel):
    count: int
    subscriptions: List[SubscriptionResponse]

class UserPaymentIssuesResponse(BaseModel):
    user_id: str
    total_failed_payments: int
    recent_failed_count: int
    last_failed_payment: str | None
    common_error_messages: Dict[str, int]

@router.get("/statistics", response_model=PaymentStatisticsResponse)
async def get_payment_statistics(
    hours: int = Query(24, ge=1, le=720, description="Часов для анализа"),
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    logger.info(f"Admin {admin_user.id} requested payment statistics for {hours}h")

    stats = await PaymentMonitoringService.get_payment_statistics(db, hours=hours)

    return PaymentStatisticsResponse(**stats)

@router.get("/stuck", response_model=StuckPaymentsResponse)
async def get_stuck_payments(
    minutes: int = Query(15, ge=5, le=120, description="Минут в статусе PENDING"),
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    logger.info(f"Admin {admin_user.id} checking stuck payments (>{minutes} min)")

    payments = await PaymentMonitoringService.get_stuck_payments(db, minutes=minutes)

    return StuckPaymentsResponse(
        count=len(payments),
        payments=[PaymentResponse.model_validate(p) for p in payments]
    )

@router.get("/failed", response_model=FailedPaymentsResponse)
async def get_failed_payments(
    hours: int = Query(24, ge=1, le=720, description="Часов для анализа"),
    limit: int = Query(100, ge=1, le=500, description="Максимум платежей"),
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    logger.info(f"Admin {admin_user.id} checking failed payments (last {hours}h)")

    payments = await PaymentMonitoringService.get_failed_payments(
        db, hours=hours, limit=limit
    )

    return FailedPaymentsResponse(
        count=len(payments),
        payments=[PaymentResponse.model_validate(p) for p in payments]
    )

@router.post("/mark-expired")
async def mark_expired_payments(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    logger.info(f"Admin {admin_user.id} reconciling overdue payments")

    count = await PaymentMonitoringService.mark_expired_payments(db)

    return {
        "status": "ok",
        "reconciled": count,
        "message": f"Проверено {count} платежей у провайдера"
    }

@router.get("/expiring-subscriptions", response_model=ExpiringSubscriptionsResponse)
async def get_expiring_subscriptions(
    days: int = Query(7, ge=1, le=30, description="Дней до истечения"),
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    logger.info(f"Admin {admin_user.id} checking expiring subscriptions ({days} days)")

    subscriptions = await PaymentMonitoringService.check_expiring_subscriptions(
        db, days=days
    )

    return ExpiringSubscriptionsResponse(
        count=len(subscriptions),
        subscriptions=[SubscriptionResponse.model_validate(s) for s in subscriptions]
    )

@router.get("/user-issues/{user_id}", response_model=UserPaymentIssuesResponse)
async def get_user_payment_issues(
    user_id: UUID,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    logger.info(f"Admin {admin_user.id} checking payment issues for user {user_id}")

    issues = await PaymentMonitoringService.get_user_payment_issues(db, user_id)

    return UserPaymentIssuesResponse(**issues)

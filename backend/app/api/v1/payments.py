import asyncio
from uuid import UUID

from app.api.checkout_response import checkout_response
from app.api.dependencies import get_current_active_user
from app.core.database import get_db
from app.models import Payment, User
from app.models.enums import PaymentType
from app.schemas.checkout import CheckoutRequest, CheckoutResponse
from app.schemas.payment import PaymentResponse
from app.services.auth_limits import reserve_attempt
from app.services.payment_lifecycle import accept_provider_state, begin_checkout, require_payments
from app.services.yookassa_service import YooKassaService
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/payments", tags=["Платежи"])


class PaymentListResponse(BaseModel):
    items: list[PaymentResponse]
    total: int
    page: int
    size: int
    pages: int


@router.post(
    "",
    response_model=CheckoutResponse,
    status_code=201,
    responses={202: {"model": CheckoutResponse, "description": "Pending provider recovery"}},
)
async def create_payment(
    data: CheckoutRequest,
    response: Response,
    idempotency_key: UUID = Header(alias="Idempotency-Key"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    payment = await begin_checkout(db, current_user.id, data, idempotency_key)
    return checkout_response(payment, response)


@router.get("", response_model=PaymentListResponse)
async def get_my_payments(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    payment_type: PaymentType | None = None,
    status_filter: str | None = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    filters = [Payment.user_id == current_user.id]
    if payment_type:
        filters.append(Payment.payment_type == payment_type)
    if status_filter:
        filters.append(Payment.status == status_filter)
    total = await db.scalar(select(func.count()).select_from(Payment).where(*filters)) or 0
    payments = (
        await db.scalars(
            select(Payment)
            .where(*filters)
            .order_by(Payment.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
    ).all()
    return PaymentListResponse(
        items=[PaymentResponse.model_validate(p) for p in payments],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    payment = await db.scalar(
        select(Payment).where(Payment.id == payment_id, Payment.user_id == current_user.id)
    )
    if payment is None:
        raise HTTPException(status_code=404, detail="Платёж не найден")
    return payment


@router.post("/yookassa/webhook")
async def yookassa_webhook(request: Request):
    require_payments()
    try:
        body = await request.json()
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid JSON")
    if (
        not isinstance(body, dict)
        or not isinstance(body.get("event"), str)
        or not isinstance(body.get("object"), dict)
        or not body["object"]
    ):
        raise HTTPException(status_code=400, detail="Invalid notification")
    expected = {"payment.succeeded": "succeeded", "payment.canceled": "canceled"}.get(body["event"])
    if expected is None:
        return {"status": "event_not_handled"}
    provider_id = body["object"].get("id")
    if not isinstance(provider_id, str) or not 1 <= len(provider_id) <= 100:
        raise HTTPException(status_code=400, detail="Invalid payment id")
    await reserve_attempt(
        "payment_webhook_ip",
        request.client.host if request.client else "unknown",
        limit=120,
        seconds=60,
    )
    try:
        async with asyncio.timeout(15):
            remote = await asyncio.to_thread(YooKassaService.get_payment_info, provider_id)
    except Exception:
        raise HTTPException(status_code=502, detail="Payment verification unavailable")
    if remote.id != provider_id or remote.status != expected:
        raise HTTPException(status_code=409, detail="Provider status does not match notification")
    processed = await accept_provider_state(remote)
    return {"status": "already_processed" if processed else "ok"}

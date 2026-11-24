"""One checkout/settlement path for HTTP, early callbacks and scheduled reconciliation."""
import asyncio
import hashlib
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import UUID, uuid4

from app.core.config import settings
from app.core.database import async_session_maker
from app.models import Order, Payment, Subscription, User
from app.models.enums import (
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    PaymentType,
    SubscriptionTier,
)
from app.schemas.checkout import CheckoutRequest
from app.services.auth_limits import reserve_attempt
from app.services.yookassa_service import ProviderRejected, YooKassaService
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

PRICES = {SubscriptionTier.BASIC: Decimal("5.00"), SubscriptionTier.PREMIUM: Decimal("10.00")}


def now():
    return datetime.now(timezone.utc)


def require_payments():
    if not settings.PAYMENTS_ENABLED:
        raise HTTPException(status_code=503, detail="Оплата временно недоступна")


async def load_payment(payment_id: UUID) -> Payment:
    async with async_session_maker() as db:
        payment = await db.get(Payment, payment_id)
        if payment is None:
            raise HTTPException(status_code=404, detail="Платёж не найден")
        return payment


async def begin_checkout(
    db: AsyncSession, user_id: UUID, data: CheckoutRequest, key: UUID
) -> Payment:
    # Release the read-only auth transaction before the separately durable budget.
    await db.commit()
    await reserve_attempt("checkout_user", str(user_id), limit=10, seconds=60)
    canonical = data.model_dump(mode="json")
    canonical["amount"] = f"{data.amount:.2f}"
    fingerprint = hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()
    # All per-user checkout/settlement writers acquire User before Payment.
    owner = await db.scalar(
        select(User)
        .where(User.id == user_id)
        .execution_options(populate_existing=True)
        .with_for_update(of=User)
    )
    if not owner or not owner.is_active:
        raise HTTPException(status_code=403, detail="Пользователь недоступен")
    existing = await db.scalar(
        select(Payment).where(Payment.user_id == user_id, Payment.idempotency_key == key)
    )
    if existing:
        if existing.request_hash != fingerprint:
            raise HTTPException(
                status_code=409, detail="Ключ идемпотентности уже использован для другого запроса"
            )
        payment_id = existing.id
        await db.commit()
        return await recover_payment(payment_id)
    if data.payment_type == PaymentType.ORDER_PAYMENT:
        if not data.order_id or data.subscription_tier or data.duration_months:
            raise HTTPException(status_code=400, detail="Укажите только order_id для оплаты заказа")
        order = await db.scalar(
            select(Order).where(Order.id == data.order_id, Order.client_id == user_id)
        )
        if order is None:
            raise HTTPException(status_code=404, detail="Заказ не найден")
        if order.status in (OrderStatus.CANCELLED, OrderStatus.FAILED):
            raise HTTPException(status_code=409, detail="Отменённый заказ нельзя оплатить")
        amount = Decimal(str(order.final_price))
        previous = await db.scalar(
            select(Payment)
            .where(
                Payment.order_id == order.id,
                Payment.status.in_([PaymentStatus.PENDING, PaymentStatus.COMPLETED]),
            )
            .limit(1)
        )
        if previous:
            raise HTTPException(
                status_code=409,
                detail="Для заказа уже существует незавершённая или успешная оплата",
            )
        description = f"Оплата заказа #{order.id}"
    elif data.payment_type == PaymentType.SUBSCRIPTION_PURCHASE:
        if data.order_id or data.subscription_tier not in PRICES or not data.duration_months:
            raise HTTPException(
                status_code=400, detail="Укажите BASIC/PREMIUM и длительность подписки"
            )
        amount = PRICES[data.subscription_tier] * data.duration_months
        description = f"Подписка {data.subscription_tier.value} на {data.duration_months} мес."
    else:
        raise HTTPException(
            status_code=400, detail="Этот тип платежа нельзя создать через checkout"
        )
    if data.amount != amount:
        raise HTTPException(status_code=400, detail="Сумма платежа не соответствует стоимости")
    if data.payment_type == PaymentType.ORDER_PAYMENT and order.status != OrderStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="Заказ оплачивается после выполнения")
    require_payments()
    payment_id = uuid4()
    metadata = {
        "payment_id": str(payment_id),
        "user_id": str(user_id),
        "payment_type": data.payment_type.value,
    }
    if data.subscription_tier:
        metadata.update(
            tier=data.subscription_tier.value, duration_months=str(data.duration_months)
        )
    instant = now()
    return_parts = urlsplit(settings.yookassa_return_url_computed)
    return_query = dict(parse_qsl(return_parts.query))
    return_query["payment_id"] = str(payment_id)
    return_url = urlunsplit(return_parts._replace(query=urlencode(return_query)))
    db.add(
        Payment(
            id=payment_id,
            user_id=user_id,
            order_id=data.order_id,
            amount=amount,
            payment_type=data.payment_type,
            payment_method=PaymentMethod.CARD,
            status=PaymentStatus.PENDING,
            currency=settings.PAYMENT_CURRENCY,
            idempotency_key=key,
            request_hash=fingerprint,
            creation_state="NEW",
            provider_key=uuid4(),
            provider_key_deadline=instant + timedelta(hours=23),
            next_reconcile_at=instant,
            checkout_expires_at=instant + timedelta(minutes=15),
            checkout_payload={
                "description": description,
                "return_url": return_url,
                "save_payment_method": data.save_payment_method,
                "metadata": metadata,
            },
        )
    )
    await db.commit()  # durable intent exists before any provider call
    return await recover_payment(payment_id)


def verify_remote(payment: Payment, remote):
    metadata = dict(getattr(remote, "metadata", None) or {})
    if (
        not isinstance(remote.id, str)
        or not remote.id
        or (payment.yookassa_payment_id and payment.yookassa_payment_id != remote.id)
        or Decimal(str(remote.amount.value)) != payment.amount
        or remote.amount.currency != payment.currency
        or metadata.get("payment_id") != str(payment.id)
        or metadata.get("user_id") != str(payment.user_id)
    ):
        raise HTTPException(status_code=409, detail="Provider payment does not match local record")
    if payment.checkout_payload:
        expected = payment.checkout_payload["metadata"]
        if any(metadata.get(key) != value for key, value in expected.items()):
            raise HTTPException(
                status_code=409, detail="Provider metadata does not match immutable checkout"
            )
    if remote.status not in ("pending", "waiting_for_capture", "succeeded", "canceled"):
        raise HTTPException(status_code=409, detail="Unknown provider payment status")
    return metadata


async def apply_remote(db: AsyncSession, payment: Payment, remote) -> bool:
    """Caller holds User then Payment locks. Return whether settlement was already applied."""
    metadata = verify_remote(payment, remote)
    already_processed = (
        payment.settlement_applied_at is not None or payment.status == PaymentStatus.COMPLETED
    )
    if remote.status == "canceled" and already_processed:
        raise HTTPException(status_code=409, detail="A settled payment cannot be canceled locally")
    payment.yookassa_payment_id = remote.id
    payment.creation_state = "READY"
    confirmation = getattr(remote, "confirmation", None)
    if confirmation and getattr(confirmation, "confirmation_url", None):
        target = urlsplit(str(confirmation.confirmation_url))
        if target.scheme != "https" or not target.hostname or target.username or target.password:
            raise HTTPException(status_code=409, detail="Invalid provider confirmation URL")
        payment.confirmation_url = str(confirmation.confirmation_url)
    payment.error_message = None
    payment.next_reconcile_at = now() + timedelta(minutes=2)
    payment.yookassa_response = json.dumps(
        {
            "id": remote.id,
            "status": remote.status,
            "amount": str(payment.amount),
            "currency": payment.currency,
        }
    )
    if remote.status == "succeeded" and not already_processed:
        if payment.payment_type == PaymentType.SUBSCRIPTION_PURCHASE:
            tier_text = metadata.get("tier")
            try:
                tier, months = SubscriptionTier(tier_text), int(
                    metadata.get("duration_months", "0")
                )
            except (ValueError, TypeError):
                raise HTTPException(status_code=409, detail="Invalid subscription metadata")
            if (
                tier not in PRICES
                or not 1 <= months <= 12
                or (not payment.checkout_payload and payment.amount != PRICES[tier] * months)
            ):
                raise HTTPException(status_code=409, detail="Invalid subscription entitlement")
            subscription = await db.scalar(
                select(Subscription)
                .where(Subscription.user_id == payment.user_id)
                .with_for_update(of=Subscription)
            )
            instant = now()
            if subscription is None:
                subscription = Subscription(
                    user_id=payment.user_id,
                    tier=tier,
                    start_date=instant,
                    end_date=instant,
                    is_active=True,
                )
                db.add(subscription)
            extend = (
                subscription.is_active
                and subscription.tier == tier
                and subscription.end_date > instant
            )
            base = subscription.end_date if extend else instant
            if not extend:
                subscription.start_date = instant
            subscription.end_date = base + timedelta(days=30 * months)
            subscription.tier = tier
            subscription.is_active = True
            subscription.last_payment_id = payment.id
            # Saving a card is not a recurring-billing implementation or a payment.
            method = getattr(remote, "payment_method", None)
            if method and getattr(method, "saved", False):
                subscription.yookassa_payment_method_id = getattr(method, "id", None)
            subscription.auto_renew_enabled = False
            subscription.next_billing_date = None
            await db.flush()
            payment.subscription_id = subscription.id
        payment.status = PaymentStatus.COMPLETED
        payment.completed_at = now()
        payment.settlement_applied_at = now()
        payment.failed_at = payment.cancelled_at = None
    elif remote.status == "succeeded" and already_processed:
        payment.status = PaymentStatus.COMPLETED
        payment.completed_at = payment.completed_at or payment.settlement_applied_at
    elif remote.status == "canceled" and not already_processed:
        payment.status = PaymentStatus.CANCELLED
        payment.cancelled_at = now()
    if payment.status in (PaymentStatus.COMPLETED, PaymentStatus.CANCELLED):
        payment.next_reconcile_at = None
    elif remote.status == "waiting_for_capture" or not payment.confirmation_url:
        payment.creation_state = "REVIEW"
        payment.error_message = "Provider confirmation requires manual review"
        payment.next_reconcile_at = None
    return already_processed


async def accept_provider_state(remote):
    metadata = dict(getattr(remote, "metadata", None) or {})
    async with async_session_maker() as db:
        payment = await db.scalar(select(Payment).where(Payment.yookassa_payment_id == remote.id))
        if payment is None:
            try:
                payment = await db.get(Payment, UUID(metadata.get("payment_id", "")))
            except (ValueError, TypeError, AttributeError):
                payment = None
        if payment is None:
            raise HTTPException(status_code=503, detail="Local payment intent is not available yet")
        payment_id, user_id = payment.id, payment.user_id
        await db.execute(select(User).where(User.id == user_id).with_for_update(of=User))
        payment = await db.scalar(
            select(Payment)
            .where(Payment.id == payment_id)
            .execution_options(populate_existing=True)
            .with_for_update(of=Payment)
        )
        processed = await apply_remote(db, payment, remote)
        await db.commit()
        return processed


async def recover_payment(payment_id: UUID, *, force=False) -> Payment:
    require_payments()
    lease = uuid4()
    async with async_session_maker() as db:
        payment = await db.scalar(
            select(Payment).where(Payment.id == payment_id).with_for_update(of=Payment)
        )
        if payment is None:
            raise HTTPException(status_code=404, detail="Платёж не найден")
        if payment.status == PaymentStatus.COMPLETED or (
            payment.status in (PaymentStatus.CANCELLED, PaymentStatus.FAILED) and not force
        ):
            return payment
        instant = now()
        if payment.lease_until and payment.lease_until > instant:
            return payment
        if not force and payment.next_reconcile_at and payment.next_reconcile_at > instant:
            return payment
        if payment.creation_state == "REVIEW" and not force:
            return payment
        provider_id = payment.yookassa_payment_id
        if not provider_id and (
            not payment.checkout_payload
            or not payment.provider_key_deadline
            or instant >= payment.provider_key_deadline
        ):
            payment.creation_state = "REVIEW"
            payment.error_message = (
                "Provider identity requires manual reconciliation; create retry is disabled"
            )
            payment.next_reconcile_at = None
            await db.commit()
            return await load_payment(payment_id)
        payment.creation_lease, payment.lease_until = lease, instant + timedelta(seconds=60)
        payment.reconcile_attempts += 1
        payload, amount, currency, provider_key = (
            payment.checkout_payload,
            payment.amount,
            payment.currency,
            payment.provider_key,
        )
        await db.commit()  # release the payment lock before external I/O
    error = None
    try:
        async with asyncio.timeout(15):
            if provider_id:
                remote = await asyncio.to_thread(YooKassaService.get_payment_info, provider_id)
            else:
                remote = await asyncio.to_thread(
                    YooKassaService.create_payment,
                    amount=amount,
                    currency=currency,
                    idempotence_key=str(provider_key),
                    **payload,
                )
        if provider_id and remote.id != provider_id:
            raise HTTPException(status_code=409, detail="Provider returned another payment")
        await accept_provider_state(remote)
    except Exception as exc:
        error = exc
    async with async_session_maker() as db:
        payment = await db.scalar(
            select(Payment).where(Payment.id == payment_id).with_for_update(of=Payment)
        )
        if payment.creation_lease == lease:
            payment.creation_lease = payment.lease_until = None
            if error and payment.status == PaymentStatus.PENDING:
                payment.error_message = type(error).__name__
                payment.next_reconcile_at = now() + timedelta(
                    seconds=min(300, 2 ** min(payment.reconcile_attempts, 9))
                )
                if isinstance(error, ProviderRejected) and not payment.yookassa_payment_id:
                    payment.status, payment.creation_state = PaymentStatus.FAILED, "FAILED"
                    payment.failed_at, payment.next_reconcile_at = now(), None
                elif isinstance(error, HTTPException):
                    payment.creation_state, payment.next_reconcile_at = "REVIEW", None
            await db.commit()
    return await load_payment(payment_id)


async def reconcile_batch(limit=20):
    if not settings.PAYMENTS_ENABLED:
        return 0
    async with async_session_maker() as db:
        ids = list(
            (
                await db.scalars(
                    select(Payment.id)
                    .where(
                        Payment.status == PaymentStatus.PENDING,
                        Payment.creation_state != "REVIEW",
                        (Payment.next_reconcile_at.is_(None))
                        | (Payment.next_reconcile_at <= now()),
                    )
                    .order_by(Payment.created_at)
                    .limit(limit)
                )
            ).all()
        )
    for payment_id in ids:
        await recover_payment(payment_id)
    return len(ids)

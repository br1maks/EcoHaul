import asyncio
from datetime import datetime, timedelta, timezone
from threading import Event
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from app.core.database import async_session_maker
from app.models import Order, Payment, Subscription
from app.services import payment_lifecycle as lifecycle
from app.services.yookassa_service import ProviderRejected, YooKassaService
from sqlalchemy import func, select, update
from tests.test_orders import login, order_for

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


def remote(**request):
    return SimpleNamespace(
        id="provider-" + request["idempotence_key"],
        status="pending",
        amount=SimpleNamespace(value=str(request["amount"]), currency=request["currency"]),
        metadata=request["metadata"],
        confirmation=SimpleNamespace(confirmation_url="https://example.test/pay"),
        payment_method=None,
    )


async def checkout(client, headers, key=None, **data):
    return await client.post(
        "/api/v1/payments",
        headers={**headers, "Idempotency-Key": str(key or uuid4())},
        json={
            "payment_type": "SUBSCRIPTION_PURCHASE",
            "amount": 5,
            "subscription_tier": "BASIC",
            "duration_months": 1,
            **data,
        },
    )


async def make_due(payment_id):
    async with async_session_maker() as db:
        await db.execute(
            update(Payment)
            .where(Payment.id == UUID(str(payment_id)))
            .values(
                next_reconcile_at=datetime.now(timezone.utc) - timedelta(seconds=1),
                lease_until=None,
            )
        )
        await db.commit()


async def test_repeated_checkout_reuses_intent_and_provider_key(client, monkeypatch):
    user = await login(client, 41001)
    calls = []

    def create(**data):
        calls.append(data)
        return remote(**data)

    monkeypatch.setattr(YooKassaService, "create_payment", create)
    key = uuid4()
    first, second = await checkout(client, user, key), await checkout(client, user, key)
    assert first.status_code == second.status_code == 201, first.text
    assert first.json()["payment_id"] == second.json()["payment_id"]
    assert len(calls) == 1
    changed = await checkout(client, user, key, duration_months=2, amount=10)
    assert changed.status_code == 409
    async with async_session_maker() as db:
        assert await db.scalar(select(func.count()).select_from(Payment)) == 1


async def test_uncertain_creation_is_retried_with_exact_same_key_and_payload(client, monkeypatch):
    user = await login(client, 42001)
    calls = []

    def create(**data):
        calls.append(data)
        if len(calls) == 1:
            raise TimeoutError("private provider response")
        return remote(**data)

    monkeypatch.setattr(YooKassaService, "create_payment", create)
    key = uuid4()
    first = await checkout(client, user, key)
    assert first.status_code == 202
    payment_id = first.json()["payment_id"]
    saved = await lifecycle.load_payment(UUID(payment_id))
    assert saved.status == "PENDING" and saved.error_message == "TimeoutError"
    await make_due(payment_id)
    second = await checkout(client, user, key)
    assert second.status_code == 201 and second.json()["payment_id"] == payment_id
    assert calls[0] == calls[1]


async def test_concurrent_checkout_does_not_issue_parallel_creation(client, monkeypatch):
    user = await login(client, 43001)
    started, release = Event(), Event()
    calls = []

    def create(**data):
        calls.append(data)
        started.set()
        assert release.wait(10)
        return remote(**data)

    monkeypatch.setattr(YooKassaService, "create_payment", create)
    key = uuid4()
    first_task = asyncio.create_task(checkout(client, user, key))
    try:
        assert await asyncio.to_thread(started.wait, 5)
        second = await checkout(client, user, key)
        assert second.status_code == 202
    finally:
        release.set()
    first = await first_task
    assert first.json()["payment_id"] == second.json()["payment_id"]
    assert len(calls) == 1


async def test_early_callback_resolves_durable_intent_before_create_returns(client, monkeypatch):
    user = await login(client, 44001)
    loop = asyncio.get_running_loop()
    response_statuses = []

    def create(**data):
        payment = remote(**data)
        payment.status = "succeeded"
        monkeypatch.setattr(YooKassaService, "get_payment_info", lambda _: payment)
        response = asyncio.run_coroutine_threadsafe(
            client.post(
                "/api/v1/payments/yookassa/webhook",
                json={"event": "payment.succeeded", "object": {"id": payment.id}},
            ),
            loop,
        ).result(timeout=10)
        response_statuses.append(response.status_code)
        return payment

    monkeypatch.setattr(YooKassaService, "create_payment", create)
    result = await checkout(client, user)
    assert result.status_code == 201 and result.json()["status"] == "COMPLETED", result.text
    assert response_statuses == [200]
    async with async_session_maker() as db:
        assert await db.scalar(select(func.count()).select_from(Subscription)) == 1


async def test_paid_extension_updates_existing_free_subscription_once(client, monkeypatch):
    user = await login(client, 45001)
    assert (await client.get("/api/v1/subscriptions/me", headers=user)).status_code == 200

    def create(**data):
        payment = remote(**data)
        payment.status = "succeeded"
        return payment

    monkeypatch.setattr(YooKassaService, "create_payment", create)
    first = await checkout(client, user)
    assert first.json()["status"] == "COMPLETED", first.text
    async with async_session_maker() as db:
        subscription = await db.scalar(select(Subscription))
        before = subscription.end_date
        subscription_id = subscription.id
        payment = await db.get(Payment, UUID(first.json()["payment_id"]))
        assert payment.settlement_applied_at is not None
        # Recovery uses the durable effect marker even if only status was corrupted.
        payment.status = "PENDING"
        snapshot = remote(
            amount=payment.amount,
            currency=payment.currency,
            idempotence_key=str(payment.provider_key),
            metadata=payment.checkout_payload["metadata"],
        )
        snapshot.status = "succeeded"
        await db.commit()
    assert await lifecycle.accept_provider_state(snapshot) is True
    async with async_session_maker() as db:
        assert (await db.get(Subscription, subscription_id)).end_date == before
    second = await checkout(client, user)
    assert second.json()["status"] == "COMPLETED"
    async with async_session_maker() as db:
        assert await db.scalar(select(func.count()).select_from(Subscription)) == 1
        subscription = await db.get(Subscription, subscription_id)
        assert subscription.end_date == before + timedelta(days=30)
        assert subscription.auto_renew_enabled is False


async def test_expired_provider_key_never_recreates_unknown_payment(client, monkeypatch):
    user = await login(client, 46001)
    monkeypatch.setattr(
        YooKassaService, "create_payment", lambda **data: (_ for _ in ()).throw(TimeoutError())
    )
    first = await checkout(client, user)
    payment_id = UUID(first.json()["payment_id"])
    async with async_session_maker() as db:
        await db.execute(
            update(Payment)
            .where(Payment.id == payment_id)
            .values(
                provider_key_deadline=datetime.now(timezone.utc) - timedelta(seconds=1),
                next_reconcile_at=None,
            )
        )
        await db.commit()
    monkeypatch.setattr(
        YooKassaService, "create_payment", lambda **data: pytest.fail("unsafe create retry")
    )
    payment = await lifecycle.recover_payment(payment_id)
    assert payment.status == "PENDING" and payment.creation_state == "REVIEW"


async def test_explicit_provider_rejection_is_distinct_from_timeout(client, monkeypatch):
    user = await login(client, 47001)

    def rejected(**data):
        raise ProviderRejected("do not expose provider details")

    monkeypatch.setattr(YooKassaService, "create_payment", rejected)
    response = await checkout(client, user)
    assert response.json()["status"] == "FAILED"
    payment = await lifecycle.load_payment(UUID(response.json()["payment_id"]))
    assert payment.error_message == "ProviderRejected"


async def test_reconciliation_recovers_missing_webhook(client, monkeypatch):
    user = await login(client, 48001)
    created = []

    def create(**data):
        payment = remote(**data)
        created.append(payment)
        return payment

    monkeypatch.setattr(YooKassaService, "create_payment", create)
    first = await checkout(client, user)
    payment_id = UUID(first.json()["payment_id"])
    created[0].status = "succeeded"
    monkeypatch.setattr(YooKassaService, "get_payment_info", lambda _: created[0])
    await make_due(payment_id)
    assert await lifecycle.reconcile_batch() == 1
    assert (await lifecycle.load_payment(payment_id)).status == "COMPLETED"
    assert await lifecycle.reconcile_batch() == 0


async def test_checkout_recovers_after_provider_success_and_local_finalize_failure(
    client, monkeypatch
):
    user = await login(client, 49001)
    calls = []

    def create(**data):
        calls.append(data)
        return remote(**data)

    monkeypatch.setattr(YooKassaService, "create_payment", create)
    original = lifecycle.accept_provider_state

    async def unavailable(remote):
        raise RuntimeError("database unavailable after provider succeeded")

    with monkeypatch.context() as patch:
        patch.setattr(lifecycle, "accept_provider_state", unavailable)
        key = uuid4()
        first = await checkout(client, user, key)
        assert first.status_code == 202
    await make_due(first.json()["payment_id"])
    second = await checkout(client, user, key)
    assert second.status_code == 201
    assert calls[0] == calls[1]
    assert lifecycle.accept_provider_state == original


async def test_order_cannot_get_two_active_payments_with_different_request_keys(
    client, monkeypatch
):
    user = await login(client, 50001)
    order, _ = await order_for(client, user)
    async with async_session_maker() as db:
        await db.execute(
            update(Order).where(Order.id == UUID(order["id"])).values(status="COMPLETED")
        )
        await db.commit()
    monkeypatch.setattr(YooKassaService, "create_payment", lambda **data: remote(**data))
    body = {
        "payment_type": "ORDER_PAYMENT",
        "amount": order["final_price"],
        "order_id": order["id"],
        "subscription_tier": None,
        "duration_months": None,
    }
    first, second = await checkout(client, user, **body), await checkout(client, user, **body)
    assert first.status_code == 201
    assert second.status_code == 409


async def test_unpaid_automatic_renewal_cannot_grant_entitlement(client):
    admin = await login(client, 51001, "ADMIN")
    response = await client.post("/api/v1/scheduled-tasks/renew-subscriptions", headers=admin)
    assert response.status_code == 200
    assert response.json()["success"] is False and response.json()["processed_count"] == 0

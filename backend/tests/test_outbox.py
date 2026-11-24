"""Exercise commit visibility, crash windows and stream locking with real PostgreSQL."""
import asyncio
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_maker
from app.models import Notification, Order, OrderQueue, OutboxMessage
from app.services import outbox_dispatcher as dispatcher
from app.services.outbox import queue_telegram, queue_websocket
from tests.test_orders import login, order_for

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def clear_outbox():
    async with async_session_maker() as db:
        await db.execute(delete(OutboxMessage))
        await db.commit()


async def rows():
    async with async_session_maker() as db:
        return list(
            (await db.scalars(select(OutboxMessage).order_by(OutboxMessage.sequence))).all()
        )


async def seed_messages(*streams):
    async with async_session_maker() as db:
        for index, stream in enumerate(streams):
            queue_websocket(
                db, UUID(int=1), {"type": "TEST", "data": {"index": index}}, aggregate_key=stream
            )
        await db.commit()


async def test_uncommitted_intent_is_invisible_and_rollback_publishes_nothing(client, monkeypatch):
    sent = []

    async def deliver(message):
        sent.append(message.event_id)

    monkeypatch.setattr(dispatcher, "deliver", deliver)
    async with async_session_maker() as db:
        queue_websocket(db, uuid4(), {"type": "TEST", "data": {}})
        await db.flush()
        assert not await dispatcher.dispatch_one("websocket")
        await db.rollback()
    assert not await dispatcher.dispatch_one("websocket")
    assert sent == [] and await rows() == []


async def test_committed_intent_survives_new_dispatcher_session(client, monkeypatch):
    await seed_messages("order:1")
    event_id = (await rows())[0].event_id
    sent = []

    async def deliver(message):
        sent.append(message.event_id)

    monkeypatch.setattr(dispatcher, "deliver", deliver)
    assert await dispatcher.dispatch_one("websocket")
    assert not await dispatcher.dispatch_one("websocket")
    saved = (await rows())[0]
    assert sent == [event_id]
    assert saved.delivered_at is not None and saved.attempts == 1


async def test_retry_blocks_only_its_stream_and_preserves_event_identity(client, monkeypatch):
    await seed_messages("order:1", "order:1", "order:2")
    original = await rows()
    sent = []
    failed = False

    async def deliver(message):
        nonlocal failed
        if message.sequence == original[0].sequence and not failed:
            failed = True
            raise ConnectionError("secret or private transport body must not be persisted")
        sent.append(message.event_id)

    monkeypatch.setattr(dispatcher, "deliver", deliver)
    assert await dispatcher.dispatch_one("websocket")  # head fails and backs off
    assert await dispatcher.dispatch_one("websocket")  # unrelated order can progress
    assert not await dispatcher.dispatch_one("websocket")  # newer same-order event waits
    saved = await rows()
    assert saved[0].last_error == "ConnectionError"
    assert saved[0].delivered_at is None and saved[0].attempts == 1
    assert saved[1].attempts == 0
    async with async_session_maker() as db:
        await db.execute(
            update(OutboxMessage)
            .where(OutboxMessage.sequence == original[0].sequence)
            .values(available_at=datetime.now(timezone.utc) - timedelta(seconds=1))
        )
        await db.commit()
    assert await dispatcher.dispatch_one("websocket")
    assert await dispatcher.dispatch_one("websocket")
    assert sent == [original[2].event_id, original[0].event_id, original[1].event_id]
    assert (await rows())[0].attempts == 2


async def test_concurrent_dispatcher_cannot_overtake_locked_stream_head(client, monkeypatch):
    await seed_messages("order:1", "order:1")
    started, release = asyncio.Event(), asyncio.Event()
    sent = []

    async def deliver(message):
        started.set()
        await release.wait()
        sent.append(message.event_id)

    monkeypatch.setattr(dispatcher, "deliver", deliver)
    first = asyncio.create_task(dispatcher.dispatch_one("websocket"))
    try:
        await asyncio.wait_for(started.wait(), timeout=5)
        assert not await dispatcher.dispatch_one("websocket")
    finally:
        release.set()
        await first
    assert await dispatcher.dispatch_one("websocket")
    assert sent == [row.event_id for row in await rows()]


async def test_crash_after_send_before_ack_retries_with_same_event_id(client, monkeypatch):
    await seed_messages("order:1")
    sent = []

    async def crash_after_send(message):
        sent.append(message.event_id)
        raise asyncio.CancelledError()  # process shutdown before the delivery transaction commits

    monkeypatch.setattr(dispatcher, "deliver", crash_after_send)
    with pytest.raises(asyncio.CancelledError):
        await dispatcher.dispatch_one("websocket")
    saved = (await rows())[0]
    assert saved.delivered_at is None and saved.attempts == 0

    async def deliver(message):
        sent.append(message.event_id)

    monkeypatch.setattr(dispatcher, "deliver", deliver)
    assert await dispatcher.dispatch_one("websocket")
    assert sent == [saved.event_id, saved.event_id]


async def test_accept_commit_failure_rolls_back_domain_inbox_and_outbox(client, monkeypatch):
    customer = await login(client, 21001)
    courier = await login(client, 21002, "COURIER")
    order, _ = await order_for(client, customer)
    await clear_outbox()
    sent = []

    async def deliver(message):
        sent.append(message.event_id)

    async def fail_commit(db):
        await db.flush()
        assert not await dispatcher.dispatch_one("websocket")
        raise RuntimeError("Injected commit failure")

    monkeypatch.setattr(dispatcher, "deliver", deliver)
    with monkeypatch.context() as patch:
        patch.setattr(AsyncSession, "commit", fail_commit)
        with pytest.raises(RuntimeError, match="Injected commit failure"):
            await client.post(f"/api/v1/orders/{order['id']}/accept", headers=courier)
    async with async_session_maker() as db:
        saved = await db.get(Order, UUID(order["id"]))
        assert saved.status == "PENDING" and saved.courier_id is None
        assert await db.scalar(select(func.count()).select_from(Notification)) == 0
        assert await db.scalar(select(func.count()).select_from(OrderQueue)) == 0
    assert await rows() == [] and sent == []


async def test_transport_failure_does_not_fail_a_committed_http_command(client, monkeypatch):
    customer = await login(client, 22001)
    courier = await login(client, 22002, "COURIER")
    order, _ = await order_for(client, customer)
    await clear_outbox()

    async def unavailable(message):
        raise ConnectionError("Transport offline")

    monkeypatch.setattr(dispatcher, "deliver", unavailable)
    response = await client.post(f"/api/v1/orders/{order['id']}/accept", headers=courier)
    assert response.status_code == 200
    assert response.json()["status"] == "ASSIGNED"
    assert await dispatcher.dispatch_one("websocket")
    assert await dispatcher.dispatch_one("cache")
    assert all(row.delivered_at is None for row in await rows())
    async with async_session_maker() as db:
        assert (await db.get(Order, UUID(order["id"]))).status == "ASSIGNED"


async def test_telegram_disabled_mode_never_accumulates_messages(client, monkeypatch):
    async with async_session_maker() as db:
        queue_telegram(db, 123, "Local demo")
        await db.commit()
    assert await rows() == []
    monkeypatch.setattr(settings, "TELEGRAM_ENABLED", True)
    async with async_session_maker() as db:
        queue_telegram(db, 123, "Enabled intent")
        await db.commit()
    monkeypatch.setattr(settings, "TELEGRAM_ENABLED", False)
    assert not await dispatcher.dispatch_one("telegram")
    assert (await rows())[0].attempts == 0


async def test_order_status_notification_is_recoverable_over_http(client):
    customer = await login(client, 23001)
    courier = await login(client, 23002, "COURIER")
    order, _ = await order_for(client, customer)
    url = f"/api/v1/orders/{order['id']}"
    assert (await client.post(url + "/accept", headers=courier)).status_code == 200
    assert (
        await client.patch(url + "/status", headers=courier, json={"status": "IN_PROGRESS"})
    ).status_code == 200
    inbox = await client.get("/api/v1/notifications", headers=customer)
    assert inbox.status_code == 200, inbox.text
    assert {item["notification_type"] for item in inbox.json()} == {
        "ORDER_ASSIGNED",
        "ORDER_STARTED",
    }
    customer_id = inbox.json()[0]["user_id"]
    customer_messages = [
        row
        for row in await rows()
        if row.channel == "websocket" and row.payload["user_id"] == customer_id
    ]
    assert len(customer_messages) == 2
    assert all(
        row.payload["message"]["data"]["notification_id"] in {item["id"] for item in inbox.json()}
        for row in customer_messages
    )


async def test_delivery_timeout_is_persisted_for_retry(client, monkeypatch):
    await seed_messages("order:1")

    async def hang(message):
        await asyncio.Event().wait()

    monkeypatch.setattr(dispatcher, "DELIVERY_TIMEOUT_SECONDS", 0.01)
    monkeypatch.setattr(dispatcher, "deliver", hang)
    assert await dispatcher.dispatch_one("websocket")
    saved = (await rows())[0]
    assert saved.last_error == "TimeoutError"
    assert saved.delivered_at is None and saved.attempts == 1


async def test_explicit_discard_unblocks_stream_without_claiming_delivery(client, monkeypatch):
    await seed_messages("order:1", "order:1")
    messages = await rows()
    async with async_session_maker() as db:
        await db.execute(
            update(OutboxMessage)
            .where(OutboxMessage.sequence == messages[0].sequence)
            .values(
                discarded_at=datetime.now(timezone.utc),
                discard_reason="Operator reviewed invalid payload",
            )
        )
        await db.commit()
    sent = []

    async def deliver(message):
        sent.append(message.event_id)

    monkeypatch.setattr(dispatcher, "deliver", deliver)
    assert await dispatcher.dispatch_one("websocket")
    assert sent == [messages[1].event_id]
    assert (await rows())[0].delivered_at is None


async def test_expiration_worker_commit_failure_rolls_back_order_and_events(client, monkeypatch):
    from app.tasks.orders import _cancel_expired

    customer = await login(client, 24001)
    order, _ = await order_for(client, customer)
    async with async_session_maker() as db:
        await db.execute(
            update(Order)
            .where(Order.id == UUID(order["id"]))
            .values(expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))
        )
        await db.commit()
    await clear_outbox()

    async def fail_commit(db):
        await db.flush()
        raise RuntimeError("Injected worker commit failure")

    with monkeypatch.context() as patch:
        patch.setattr(AsyncSession, "commit", fail_commit)
        with pytest.raises(RuntimeError, match="worker commit failure"):
            await _cancel_expired()
    async with async_session_maker() as db:
        assert (await db.get(Order, UUID(order["id"]))).status == "PENDING"
        assert await db.scalar(select(func.count()).select_from(Notification)) == 0
    assert await rows() == []


async def test_bulk_failure_rolls_back_every_claim_and_event(client, monkeypatch):
    from app.core.security import hash_password
    from app.models import User

    customer = await login(client, 25001)
    courier = await login(client, 25002, "COURIER")
    orders = [(await order_for(client, customer))[0] for _ in range(2)]
    async with async_session_maker() as db:
        await db.execute(
            update(User)
            .where(User.telegram_id == 25002)
            .values(password_hash=hash_password("test-only-password"))
        )
        await db.commit()
    await clear_outbox()
    from app.api.v1 import orders as routes

    original = routes._accept_locked_order
    calls = 0

    async def fail_second(db, order, user):
        nonlocal calls
        calls += 1
        await original(db, order, user)
        if calls == 2:
            raise RuntimeError("Injected second-item failure")

    monkeypatch.setattr(routes, "_accept_locked_order", fail_second)
    with pytest.raises(RuntimeError, match="second-item failure"):
        await client.post(
            "/api/v1/orders/accept-bulk",
            headers=courier,
            json={"order_ids": [item["id"] for item in orders], "password": "test-only-password"},
        )
    async with async_session_maker() as db:
        saved = (await db.scalars(select(Order))).all()
        assert all(item.status == "PENDING" and item.courier_id is None for item in saved)
        assert await db.scalar(select(func.count()).select_from(Notification)) == 0
    assert await rows() == []


async def test_administrator_assignment_persists_both_recipient_events(client):
    from app.models import User

    customer = await login(client, 26001)
    await login(client, 26002, "COURIER")
    admin = await login(client, 26003, "ADMIN")
    order, _ = await order_for(client, customer)
    await clear_outbox()
    async with async_session_maker() as db:
        courier = await db.scalar(select(User).where(User.telegram_id == 26002))
        courier_id = courier.id
    response = await client.patch(
        f"/api/v1/orders/{order['id']}/assign-courier",
        headers=admin,
        params={"courier_id": str(courier_id)},
    )
    assert response.status_code == 200, response.text
    messages = [row for row in await rows() if row.channel == "websocket"]
    assert len(messages) == 2
    assert {row.payload["message"]["type"] for row in messages} == {
        "NEW_NOTIFICATION",
        "ORDER_ASSIGNED",
    }


async def test_shift_end_queues_event_with_its_state_change(client):
    courier = await login(client, 27001, "COURIER")
    assert (await client.post("/api/v1/courier-shifts/start", headers=courier)).status_code == 201
    response = await client.post("/api/v1/courier-shifts/end", headers=courier)
    assert response.status_code == 200, response.text
    assert response.json()["ended_at"] is not None
    assert [row.payload["message"]["type"] for row in await rows()] == ["SHIFT_ENDED"]


@pytest.mark.parametrize("command", ["notify-expiring-subscriptions"])
async def test_subscription_commands_commit_inbox_and_delivery_together(client, command):
    from app.models import Subscription, User

    await login(client, 28001)
    admin = await login(client, 28002, "ADMIN")
    now = datetime.now(timezone.utc)
    async with async_session_maker() as db:
        user = await db.scalar(select(User).where(User.telegram_id == 28001))
        db.add(
            Subscription(
                user_id=user.id,
                tier="BASIC",
                start_date=now - timedelta(days=30),
                end_date=now + timedelta(days=3, hours=1)
                if command.startswith("notify")
                else now - timedelta(days=1),
                auto_renew_enabled=True,
                is_active=True,
            )
        )
        await db.commit()
    response = await client.post(f"/api/v1/scheduled-tasks/{command}", headers=admin)
    assert response.status_code == 200, response.text
    assert response.json()["success"] is True, response.text
    assert response.json()["processed_count"] == 1
    async with async_session_maker() as db:
        assert await db.scalar(select(func.count()).select_from(Notification)) == 1
    assert len(await rows()) == 1


async def test_new_order_confirmation_does_not_require_available_couriers(client, monkeypatch):
    customer = await login(client, 29001)
    monkeypatch.setattr(settings, "TELEGRAM_ENABLED", True)
    await order_for(client, customer)
    messages = [row for row in await rows() if row.channel == "telegram"]
    assert len(messages) == 1
    assert messages[0].payload["telegram_id"] == 29001


async def test_operator_status_hides_payload_and_purge_preserves_pending(client, capsys):
    from types import SimpleNamespace
    from scripts.outbox import main

    await seed_messages("order:1", "order:2")
    messages = await rows()
    async with async_session_maker() as db:
        first = await db.get(OutboxMessage, messages[0].sequence)
        first.payload = {"private": "not-for-operator-output"}
        second = await db.get(OutboxMessage, messages[1].sequence)
        second.delivered_at = datetime.now(timezone.utc) - timedelta(days=8)
        await db.commit()
    await main(SimpleNamespace(command="status"))
    assert "not-for-operator-output" not in capsys.readouterr().out
    await main(SimpleNamespace(command="purge", days=7))
    saved = await rows()
    assert [row.event_id for row in saved] == [messages[0].event_id]


async def test_deleted_inbox_entry_is_not_resurrected_by_pending_realtime_hint(client, monkeypatch):
    customer = await login(client, 30001)
    courier = await login(client, 30002, "COURIER")
    order, _ = await order_for(client, customer)
    await clear_outbox()
    assert (
        await client.post(f"/api/v1/orders/{order['id']}/accept", headers=courier)
    ).status_code == 200
    assert (
        await client.delete("/api/v1/notifications/delete-all", headers=customer)
    ).status_code == 200
    sent = []

    async def deliver(message):
        sent.append(message.payload["message"]["type"])

    monkeypatch.setattr(dispatcher, "deliver", deliver)
    while await dispatcher.dispatch_one("websocket"):
        pass
    assert sent == ["NEW_NOTIFICATION"]  # only the courier's retained inbox entry

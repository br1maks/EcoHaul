from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.core.database import async_session_maker
from app.models import Payment, User
from app.models.enums import PaymentMethod, PaymentStatus, PaymentType, UserRole
from app.services.yookassa_service import YooKassaService

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def pending_payment():
    async with async_session_maker() as db:
        user = User(telegram_id=17001, first_name='Test', last_name='User', role=UserRole.CLIENT)
        db.add(user)
        await db.flush()
        payment = Payment(user_id=user.id, payment_type=PaymentType.ORDER_PAYMENT,
                          payment_method=PaymentMethod.CARD, amount=Decimal('6.00'),
                          status=PaymentStatus.PENDING, yookassa_payment_id='provider-test-id')
        db.add(payment)
        await db.commit()
        return payment.id, user.id


def provider_object(payment_id, user_id, **overrides):
    data = dict(id='provider-test-id', status='succeeded', amount=SimpleNamespace(value='6.00', currency='BYN'),
                metadata={'payment_id': str(payment_id), 'user_id': str(user_id)}, payment_method=None)
    return SimpleNamespace(**{**data, **overrides})


async def test_verified_webhook_is_idempotent(client, monkeypatch):
    payment_id, user_id = await pending_payment()
    monkeypatch.setattr(YooKassaService, 'get_payment_info', lambda _: provider_object(payment_id, user_id))
    event = {'event': 'payment.succeeded', 'object': {'id': 'provider-test-id'}}
    first = await client.post('/api/v1/payments/yookassa/webhook', json=event)
    second = await client.post('/api/v1/payments/yookassa/webhook', json=event)
    assert first.status_code == second.status_code == 200
    assert first.json()['status'] == 'ok'
    assert second.json()['status'] == 'already_processed'
    async with async_session_maker() as db:
        assert (await db.get(Payment, payment_id)).status == PaymentStatus.COMPLETED


@pytest.mark.parametrize('mismatch', ['status', 'amount', 'currency', 'metadata'])
async def test_webhook_rejects_unverified_payment_details(client, monkeypatch, mismatch):
    payment_id, user_id = await pending_payment()
    overrides = {
        'status': {'status': 'pending'},
        'amount': {'amount': SimpleNamespace(value='0.01', currency='BYN')},
        'currency': {'amount': SimpleNamespace(value='6.00', currency='RUB')},
        'metadata': {'metadata': {'payment_id': 'wrong', 'user_id': str(user_id)}},
    }[mismatch]
    monkeypatch.setattr(YooKassaService, 'get_payment_info', lambda _: provider_object(payment_id, user_id, **overrides))
    response = await client.post('/api/v1/payments/yookassa/webhook', json={
        'event': 'payment.succeeded', 'object': {'id': 'provider-test-id', 'status': 'succeeded'},
    })
    assert response.status_code == 409
    async with async_session_maker() as db:
        assert (await db.get(Payment, payment_id)).status == PaymentStatus.PENDING


async def test_provider_failure_does_not_acknowledge_payment(client, monkeypatch):
    def unavailable(_):
        raise ConnectionError('test provider unavailable')
    monkeypatch.setattr(YooKassaService, 'get_payment_info', unavailable)
    response = await client.post('/api/v1/payments/yookassa/webhook', json={
        'event': 'payment.succeeded', 'object': {'id': 'provider-test-id'},
    })
    assert response.status_code == 502


@pytest.mark.parametrize('body', [{}, [], {'event': {}, 'object': {}}])
async def test_malformed_webhook_returns_client_error(client, body):
    assert (await client.post('/api/v1/payments/yookassa/webhook', json=body)).status_code == 400

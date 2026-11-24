import asyncio
from uuid import UUID, uuid4
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.database import async_session_maker
from app.models import Order, User

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def login(client, telegram_id, role="CLIENT"):
    response = await client.post("/api/v1/auth/test", json={
        "telegram_id": telegram_id, "first_name": "Test", "last_name": "User",
        "role": role, "is_verified": role == "COURIER",
    })
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def order_for(client, headers):
    response = await client.post("/api/v1/addresses", headers=headers, json={
        "latitude": 53.9, "longitude": 27.56, "full_address": "Минск, Аэродромная, 1",
        "city": "Минск", "district": "Октябрьский", "street": "аэродромная", "house_number": "1",
    })
    assert response.status_code == 201, response.text
    address = response.json()
    scheduled = (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=7, minute=0, second=0)
    response = await client.post("/api/v1/orders", headers=headers, json={
        "pickup_address_id": address["id"], "number_of_bags": 3,
        "garbage_type": "HOUSEHOLD", "scheduled_time": scheduled.isoformat(),
    })
    assert response.status_code == 201, response.text
    return response.json(), address


async def test_order_lifecycle_and_invalid_transition(client):
    customer = await login(client, 11001)
    courier = await login(client, 11002, "COURIER")
    order, _ = await order_for(client, customer)
    url = f"/api/v1/orders/{order['id']}"
    assert order["final_price"] == 6.0
    assert (await client.patch(url + "/status", headers=courier, json={"status": "COMPLETED"})).status_code == 403
    assert (await client.post(url + "/accept", headers=courier)).status_code == 200
    assert (await client.patch(url + "/status", headers=courier, json={"status": "COMPLETED"})).status_code == 400
    for state in ["IN_PROGRESS", "ARRIVED", "COMPLETED"]:
        response = await client.patch(url + "/status", headers=courier, json={"status": state})
        assert response.status_code == 200, response.text
        assert response.json()["status"] == state
    assert (await client.patch(url + "/status", headers=courier, json={"status": "COMPLETED"})).status_code == 400


async def test_two_couriers_cannot_claim_the_same_order(client):
    customer = await login(client, 12001)
    couriers = [await login(client, 12002, "COURIER"), await login(client, 12003, "COURIER")]
    order, _ = await order_for(client, customer)
    responses = await asyncio.gather(*(client.post(f"/api/v1/orders/{order['id']}/accept", headers=headers) for headers in couriers))
    assert sorted(response.status_code for response in responses) == [200, 400]
    async with async_session_maker() as db:
        saved = await db.get(Order, UUID(order["id"]))
        assert saved.courier_id is not None and saved.status == "ASSIGNED"


async def test_expired_order_cannot_be_claimed(client):
    customer = await login(client, 13001)
    courier = await login(client, 13002, "COURIER")
    order, _ = await order_for(client, customer)
    async with async_session_maker() as db:
        saved = (await db.execute(select(Order).where(Order.id == order["id"]))).scalar_one()
        saved.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        await db.commit()
    assert (await client.post(f"/api/v1/orders/{order['id']}/accept", headers=courier)).status_code == 400


async def test_customer_cannot_read_other_customers_data(client):
    owner = await login(client, 14001)
    stranger = await login(client, 14002)
    order, address = await order_for(client, owner)
    assert (await client.get(f"/api/v1/addresses/{address['id']}", headers=stranger)).status_code == 404
    assert (await client.get(f"/api/v1/orders/{order['id']}", headers=stranger)).status_code == 403
    assert (await client.post(f"/api/v1/orders/{order['id']}/accept", headers=stranger)).status_code == 403


async def test_checkout_rejects_customer_supplied_price(client):
    customer = await login(client, 15001)
    order, _ = await order_for(client, customer)
    response = await client.post('/api/v1/payments', headers={**customer, 'Idempotency-Key': str(uuid4())}, json={
        'payment_type': 'ORDER_PAYMENT', 'order_id': order['id'], 'amount': 0.01,
    })
    assert response.status_code == 400


async def test_blocked_user_loses_api_access(client):
    customer = await login(client, 16001)
    async with async_session_maker() as db:
        user = (await db.execute(select(User).where(User.telegram_id == 16001))).scalar_one()
        user.is_active = False
        await db.commit()
    assert (await client.get('/api/v1/users/me', headers=customer)).status_code == 403

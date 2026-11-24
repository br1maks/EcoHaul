"""One bounded HTTP/WebSocket smoke test through the actual API lifespan."""
import asyncio
import json
import os
import socket
import subprocess
import sys
from uuid import UUID

import httpx
import pytest
import websockets

from app.core.database import async_session_maker
from app.models import Order
from tests.test_orders import login, order_for


@pytest.mark.integration
@pytest.mark.asyncio
async def test_committed_assignment_reaches_socket_and_read_state_survives_http_refresh(
    client, tmp_path
):
    # Bind only localhost; all identities and credentials are synthetic test data.
    with socket.socket() as port_reservation:
        port_reservation.bind(("127.0.0.1", 0))
        port = port_reservation.getsockname()[1]
    with (tmp_path / "api.log").open("w+") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--no-access-log",
            ],
            env={**os.environ, "TELEGRAM_ENABLED": "False"},
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}", timeout=5) as http:
                async with asyncio.timeout(20):
                    while True:
                        assert process.poll() is None, "API exited before readiness"
                        try:
                            ready = await http.get("/health")
                            if ready.status_code == 200:
                                break
                        except httpx.TransportError:
                            pass
                        await asyncio.sleep(0.1)
                customer = await login(http, 31001)
                courier = await login(http, 31002, "COURIER")
                order, _ = await order_for(http, customer)
                token = customer["Authorization"].removeprefix("Bearer ")
                async with websockets.connect(
                    f"ws://127.0.0.1:{port}/api/v1/ws?token={token}"
                ) as ws:
                    connected = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
                    assert connected["type"] == "CONNECTED"
                    response = await http.post(
                        f"/api/v1/orders/{order['id']}/accept", headers=courier
                    )
                    assert response.status_code == 200, response.text
                    event = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
                    assert event["type"] == "ORDER_ASSIGNED"
                    assert UUID(event["event_id"])
                    async with async_session_maker() as db:
                        assert (await db.get(Order, UUID(order["id"]))).status == "ASSIGNED"
                    notification_id = event["data"]["notification_id"]
                    await ws.send(
                        json.dumps({"type": "MARK_READ", "notification_id": notification_id})
                    )
                    async with asyncio.timeout(5):
                        while True:
                            inbox = await http.get("/api/v1/notifications", headers=customer)
                            assert inbox.status_code == 200, inbox.text
                            saved = next(
                                item for item in inbox.json() if item["id"] == notification_id
                            )
                            if saved["is_read"]:
                                assert saved["read_at"] is not None
                                break
                            await asyncio.sleep(0.05)
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

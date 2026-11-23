from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
@pytest.mark.parametrize("database_ok,redis_ok", [(True, True), (False, True), (True, False)])
async def test_readiness_reflects_dependency_failures(monkeypatch, database_ok, redis_ok):
    connection = AsyncMock()
    if not database_ok:
        connection.execute.side_effect = ConnectionError("database unavailable")
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=connection)
    context.__aexit__ = AsyncMock(return_value=False)
    engine = MagicMock()
    engine.connect.return_value = context
    monkeypatch.setattr("app.main.engine", engine)
    redis = AsyncMock()
    if not redis_ok:
        redis.ping.side_effect = ConnectionError("redis unavailable")
    monkeypatch.setattr("app.main.get_redis", lambda: redis)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == (200 if database_ok and redis_ok else 503)
    assert response.json()["database"] == ("connected" if database_ok else "unavailable")
    assert response.json()["redis"] == ("connected" if redis_ok else "unavailable")


@pytest.mark.asyncio
async def test_dev_auth_disabled_independently_of_docs(monkeypatch):
    from app.core.config import settings
    from app.core.database import get_db

    async def unused_database():
        yield None

    monkeypatch.setattr(settings, "ENABLE_DEV_AUTH", False)
    app.dependency_overrides[get_db] = unused_database
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            assert (await client.get("/api/docs")).status_code == 200
            response = await client.post("/api/v1/auth/test", json={"telegram_id": 1, "first_name": "Test"})
            assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(get_db, None)

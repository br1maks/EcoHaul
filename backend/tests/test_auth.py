
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

class TestTestAuth:

    async def test_register_new_user(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/test", json={
            "telegram_id": 100001,
            "first_name": "Иван",
            "last_name": "Петров",
            "role": "CLIENT",
        })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_existing_user(self, client: AsyncClient):
        payload = {
            "telegram_id": 100002,
            "first_name": "Мария",
            "role": "CLIENT",
        }

        first = await client.post("/api/v1/auth/test", json=payload)
        second = await client.post("/api/v1/auth/test", json=payload)

        assert first.status_code == 200
        assert second.status_code == 200
        assert "access_token" in first.json()
        assert "access_token" in second.json()

    async def test_register_courier(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/test", json={
            "telegram_id": 200001,
            "first_name": "Курьер",
            "last_name": "Тестовый",
            "role": "COURIER",
            "is_verified": True,
        })

        assert response.status_code == 200

    async def test_register_admin(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/test", json={
            "telegram_id": 300001,
            "first_name": "Админ",
            "role": "ADMIN",
        })

        assert response.status_code == 200

    async def test_missing_required_field(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/test", json={
            "telegram_id": 100003,
        })

        assert response.status_code == 422

class TestRefreshToken:

    async def test_refresh_returns_new_tokens(self, client: AsyncClient):
        auth = await client.post("/api/v1/auth/test", json={
            "telegram_id": 100010,
            "first_name": "Рефреш",
            "role": "CLIENT",
        })
        refresh_token = auth.json()["refresh_token"]

        response = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token,
        })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_invalid_refresh_token(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": "это.не.токен",
        })

        assert response.status_code == 401

    async def test_access_token_as_refresh_rejected(self, client: AsyncClient):
        auth = await client.post("/api/v1/auth/test", json={
            "telegram_id": 100011,
            "first_name": "Тест",
            "role": "CLIENT",
        })
        access_token = auth.json()["access_token"]

        response = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": access_token,
        })

        assert response.status_code == 401

class TestAdminLogin:

    async def test_admin_login_success(self, client: AsyncClient):
        await client.post("/api/v1/auth/test", json={
            "telegram_id": 300010,
            "first_name": "Админ",
            "role": "ADMIN",
            "email": "admin@ecohaul.by",
            "password": "securepass",
        })

        response = await client.post("/api/v1/auth/admin/login", json={
            "email": "admin@ecohaul.by",
            "password": "securepass",
        })

        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_admin_login_wrong_password(self, client: AsyncClient):
        await client.post("/api/v1/auth/test", json={
            "telegram_id": 300011,
            "first_name": "Админ2",
            "role": "ADMIN",
            "email": "admin2@ecohaul.by",
            "password": "correctpass",
        })

        response = await client.post("/api/v1/auth/admin/login", json={
            "email": "admin2@ecohaul.by",
            "password": "wrongpass",
        })

        assert response.status_code == 401

    async def test_non_admin_cannot_login(self, client: AsyncClient):
        await client.post("/api/v1/auth/test", json={
            "telegram_id": 100020,
            "first_name": "Клиент",
            "role": "CLIENT",
            "email": "client@ecohaul.by",
            "password": "pass1234",
        })

        response = await client.post("/api/v1/auth/admin/login", json={
            "email": "client@ecohaul.by",
            "password": "pass1234",
        })

        assert response.status_code == 403

    async def test_nonexistent_email(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/admin/login", json={
            "email": "nobody@ecohaul.by",
            "password": "anypass",
        })

        assert response.status_code == 401

class TestProtectedRoutes:

    async def test_protected_route_without_token(self, client: AsyncClient):
        response = await client.get("/api/v1/orders")

        assert response.status_code == 401

    async def test_protected_route_with_valid_token(self, client: AsyncClient):
        auth = await client.post("/api/v1/auth/test", json={
            "telegram_id": 100030,
            "first_name": "Тест",
            "role": "CLIENT",
        })
        token = auth.json()["access_token"]

        response = await client.get(
            "/api/v1/orders",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code != 401

    async def test_admin_route_forbidden_for_client(self, client: AsyncClient):
        auth = await client.post("/api/v1/auth/test", json={
            "telegram_id": 100031,
            "first_name": "Клиент",
            "role": "CLIENT",
        })
        token = auth.json()["access_token"]

        response = await client.get(
            "/api/v1/admin/couriers",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403

    async def test_admin_route_accessible_for_admin(self, client: AsyncClient):
        auth = await client.post("/api/v1/auth/test", json={
            "telegram_id": 300020,
            "first_name": "Админ",
            "role": "ADMIN",
        })
        token = auth.json()["access_token"]

        response = await client.get(
            "/api/v1/admin/couriers",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200

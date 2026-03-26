import asyncio
import httpx

BASE_URL = "http://localhost:8000/api/v1"

async def test_accept_order():
    async with httpx.AsyncClient() as client:
        print("1. Авторизация курьера...")
        auth_response = await client.post(
            f"{BASE_URL}/auth/test",
            json={
                "telegram_id": 987654322,
                "username": "test_courier_2",
                "first_name": "Курьер",
                "last_name": "Тестовый",
                "role": "COURIER"
            }
        )

        if auth_response.status_code != 200:
            print(f"❌ Ошибка авторизации: {auth_response.status_code}")
            print(auth_response.text)
            return

        tokens = auth_response.json()
        access_token = tokens["access_token"]
        print(f"✅ Авторизация успешна")

        print("\n2. Получение доступных заказов...")
        orders_response = await client.get(
            f"{BASE_URL}/orders/available",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        if orders_response.status_code != 200:
            print(f"❌ Ошибка получения заказов: {orders_response.status_code}")
            print(orders_response.text)
            return

        orders = orders_response.json()
        if not orders:
            print("❌ Нет доступных заказов для тестирования")
            return

        order_id = orders[0]["id"]
        print(f"✅ Найден заказ: {order_id}")

        print("\n3. Попытка принять заказ с паролем...")
        accept_response = await client.post(
            f"{BASE_URL}/orders/{order_id}/accept",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"password": "courier123"}
        )

        print(f"Status: {accept_response.status_code}")
        print(f"Response: {accept_response.text}")

        if accept_response.status_code == 200:
            print("✅ Заказ успешно принят!")
        else:
            print(f"❌ Ошибка при принятии заказа")
            print("\n4. Попытка с другим форматом...")
            accept_response2 = await client.post(
                f"{BASE_URL}/orders/{order_id}/accept",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                content='{"password": "courier123"}'
            )
            print(f"Status: {accept_response2.status_code}")
            print(f"Response: {accept_response2.text}")

if __name__ == "__main__":
    asyncio.run(test_accept_order())

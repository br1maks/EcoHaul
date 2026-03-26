
import asyncio
import httpx
from jose import jwt

BASE_URL = "http://localhost:8000/api/v1"

def get_user_id_from_token(token: str) -> str:
    payload = jwt.decode(token, key="", options={"verify_signature": False})
    return payload["sub"]

async def setup_test():

    print("=" * 60)
    print("Подготовка теста WebSocket уведомлений")
    print("=" * 60)

    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        print("\n1. Создание клиента...")
        auth_response = await client.post(
            "/auth/test",
            json={
                "telegram_id": 999888777,
                "username": "ws_test_user",
                "first_name": "WebSocket",
                "last_name": "Test",
                "role": "CLIENT"
            }
        )

        if auth_response.status_code != 200:
            print(f"❌ Ошибка создания клиента: {auth_response.status_code}")
            print(auth_response.text)
            return

        client_tokens = auth_response.json()
        client_token = client_tokens["access_token"]
        print(f"✅ Клиент создан")

        print("\n2. Создание адреса...")
        address_response = await client.post(
            "/addresses",
            headers={"Authorization": f"Bearer {client_token}"},
            json={
                "street": "николы теслы",
                "house_number": "10",
                "entrance": 1,
                "floor": 5,
                "apartment": "50",
                "latitude": 53.9045,
                "longitude": 27.5615,
                "full_address": "Минск, ул. Николы Теслы, 10-50",
                "district": "Заводской"
            }
        )

        if address_response.status_code != 201:
            print(f"❌ Ошибка создания адреса: {address_response.status_code}")
            print(address_response.text)
            return

        address_data = address_response.json()
        address_id = address_data["id"]
        print(f"✅ Адрес создан: {address_data['street']}, {address_data['house_number']}")

        print("\n3. Создание заказа...")
        order_response = await client.post(
            "/orders",
            headers={"Authorization": f"Bearer {client_token}"},
            json={
                "pickup_address_id": address_id,
                "garbage_type": "HOUSEHOLD",
                "number_of_bags": 3,
                "description": "Тест WebSocket уведомлений - проверка real-time доставки"
            }
        )

        if order_response.status_code != 201:
            print(f"❌ Ошибка создания заказа: {order_response.status_code}")
            print(order_response.text)
            return

        order_data = order_response.json()
        order_id = order_data["id"]
        print(f"✅ Заказ создан!")
        print(f"   ID заказа: {order_id}")
        print(f"   Количество мешков: {order_data['number_of_bags']}")
        print(f"   Цена: {order_data['final_price']} BYN")

        print("\n4. Создание курьера...")
        courier_response = await client.post(
            "/auth/test",
            json={
                "telegram_id": 111222333,
                "username": "courier_ws_test",
                "first_name": "Курьер",
                "last_name": "WebSocket",
                "role": "COURIER"
            }
        )

        if courier_response.status_code != 200:
            print(f"❌ Ошибка создания курьера: {courier_response.status_code}")
            return

        courier_tokens = courier_response.json()
        courier_token = courier_tokens["access_token"]
        courier_id = get_user_id_from_token(courier_token)
        print(f"✅ Курьер создан")

        print("\n5. Установка пароля курьеру...")
        password_response = await client.patch(
            "/users/me",
            headers={"Authorization": f"Bearer {courier_token}"},
            json={"password": "test1234"}
        )

        if password_response.status_code != 200:
            print(f"❌ Ошибка установки пароля: {password_response.status_code}")
            print(password_response.text)
            return

        print(f"✅ Пароль установлен")

        print("\n6. Верификация курьера...")
        print(f"   Выполняется SQL: UPDATE users SET is_verified = true WHERE id = '{courier_id}'")

        import asyncpg
        conn = await asyncpg.connect(
            host="localhost",
            port=5432,
            database="ecohaul_sandbox",
            user="postgres",
            password=os.environ.get("TEST_DB_PASSWORD", "postgres")
        )
        await conn.execute(
            "UPDATE users SET is_verified = true WHERE id = $1",
            courier_id
        )
        await conn.close()
        print(f"✅ Курьер верифицирован")

        print("\n" + "=" * 60)
        print("✅ ВСЁ ГОТОВО!")
        print("=" * 60)
        print("\nТеперь выполни эту команду в другом терминале:")
        print("\n" + "-" * 60)
        print(f"""curl -X POST "http://localhost:8000/api/v1/orders/{order_id}/accept" \\
  -H "Authorization: Bearer {courier_token}" \\
  -H "Content-Type: application/json" \\
  -d '{{"password": "test1234"}}'""")
        print("-" * 60)

        print("\n📺 Смотри на терминал с test_websocket.py!")
        print("   Там должно появиться уведомление: 🔔 НОВОЕ УВЕДОМЛЕНИЕ!")
        print("\n" + "=" * 60)

if __name__ == "__main__":
    try:
        asyncio.run(setup_test())
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

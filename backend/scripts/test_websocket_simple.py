
import asyncio
import httpx

async def test_basic_connection():

    print("=" * 60)
    print("Тест WebSocket подключения")
    print("=" * 60)

    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        print("\n1. Авторизация клиента...")
        auth_response = await client.post(
            "/api/v1/auth/test",
            json={
                "telegram_id": 999888777,
                "username": "ws_test_user",
                "first_name": "WebSocket",
                "last_name": "Test",
                "role": "CLIENT"
            }
        )

        if auth_response.status_code != 200:
            print(f"❌ Ошибка авторизации: {auth_response.status_code}")
            print(auth_response.text)
            return

        tokens = auth_response.json()
        access_token = tokens["access_token"]
        print(f"✅ Токен получен: {access_token[:30]}...")

        ws_url = f"ws://localhost:8000/api/v1/ws?token={access_token}"
        print(f"\n2. WebSocket URL: {ws_url[:60]}...")
        print("✅ URL сформирован")

        print("\n" + "=" * 60)
        print("Базовая проверка завершена успешно!")
        print("=" * 60)
        print("\nДля полного теста с подключением используй:")
        print("  poetry run python test_websocket.py")

if __name__ == "__main__":
    try:
        asyncio.run(test_basic_connection())
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

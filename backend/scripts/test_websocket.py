
import asyncio
import json
from datetime import datetime

import httpx
from websockets import connect

BASE_URL = "http://localhost:8000/api/v1"
WS_URL = "ws://localhost:8000/api/v1/ws"

async def test_websocket():

    async with httpx.AsyncClient() as client:
        print("1. Авторизация клиента...")
        auth_response = await client.post(
            f"{BASE_URL}/auth/test",
            json={
                "telegram_id": 111222333,
                "username": "ws_test_client",
                "first_name": "WebSocket",
                "last_name": "Тестовый",
                "role": "CLIENT"
            }
        )

        if auth_response.status_code != 200:
            print(f"❌ Ошибка авторизации: {auth_response.status_code}")
            print(auth_response.text)
            return

        tokens = auth_response.json()
        access_token = tokens["access_token"]
        print(f"✅ Получен токен: {access_token[:50]}...")

        print("\n2. Подключение к WebSocket...")
        ws_url_with_token = f"{WS_URL}?token={access_token}"

        try:
            async with connect(ws_url_with_token) as websocket:
                print("✅ WebSocket соединение установлено!")

                print("\n3. Ожидание сообщений от сервера...")
                print("(Нажми Ctrl+C для выхода)\n")

                async def send_heartbeat():
                    while True:
                        await asyncio.sleep(20)
                        ping_message = {
                            "type": "PING",
                            "timestamp": datetime.now().isoformat()
                        }
                        await websocket.send(json.dumps(ping_message))
                        print(f"📤 Отправлен PING: {datetime.now().strftime('%H:%M:%S')}")

                heartbeat_task = asyncio.create_task(send_heartbeat())

                try:
                    async for message in websocket:
                        data = json.loads(message)
                        message_type = data.get("type")

                        if message_type == "CONNECTED":
                            print(f"🔗 {data['data']['message']}")
                            print(f"   User ID: {data['data']['user_id']}\n")

                        elif message_type == "PONG":
                            print(f"📥 Получен PONG: {datetime.now().strftime('%H:%M:%S')}")

                        elif message_type == "NEW_NOTIFICATION":
                            notif = data["data"]
                            print(f"\n🔔 НОВОЕ УВЕДОМЛЕНИЕ!")
                            print(f"   Заголовок: {notif['title']}")
                            print(f"   Сообщение: {notif['message']}")
                            print(f"   Приоритет: {notif['priority']}")
                            print(f"   Время: {notif['created_at']}\n")

                            mark_read = {
                                "type": "MARK_READ",
                                "notification_id": notif["id"]
                            }
                            await websocket.send(json.dumps(mark_read))

                        elif message_type == "ORDER_STATUS_CHANGED":
                            order_data = data["data"]
                            print(f"\n📦 ИЗМЕНИЛСЯ СТАТУС ЗАКАЗА!")
                            print(f"   Заказ ID: {order_data['order_id']}")
                            print(f"   Новый статус: {order_data['status']}")
                            print(f"   Сообщение: {order_data['message']}\n")

                        elif message_type == "NEW_ORDER":
                            order = data["data"]
                            print(f"\n🚚 НОВЫЙ ЗАКАЗ!")
                            print(f"   ID: {order['order_id']}")
                            print(f"   Откуда: {order['pickup_address']}")
                            print(f"   Куда: {order['delivery_address']}")
                            print(f"   Цена: {order['final_price']} BYN\n")

                        else:
                            print(f"❓ Неизвестный тип сообщения: {message_type}")
                            print(f"   Данные: {data}\n")

                except asyncio.CancelledError:
                    heartbeat_task.cancel()
                    raise

        except ConnectionRefusedError:
            print("❌ Не удалось подключиться к WebSocket серверу")
            print("   Проверь, что сервер запущен (poetry run uvicorn app.main:app)")
        except Exception as e:
            print(f"❌ Ошибка WebSocket: {e}")

async def test_send_notification():
    async with httpx.AsyncClient() as client:
        auth_response = await client.post(
            f"{BASE_URL}/auth/test",
            json={
                "telegram_id": 999888777,
                "username": "admin_sender",
                "first_name": "Админ",
                "last_name": "Отправитель",
                "role": "ADMIN"
            }
        )

        if auth_response.status_code != 200:
            print(f"❌ Ошибка авторизации: {auth_response.status_code}")
            return

        tokens = auth_response.json()
        access_token = tokens["access_token"]

        print("📨 Функция отправки уведомления будет реализована после интеграции")

if __name__ == "__main__":
    print("=" * 60)
    print("WebSocket Test Client")
    print("=" * 60)
    print()

    try:
        asyncio.run(test_websocket())
    except KeyboardInterrupt:
        print("\n\n👋 WebSocket соединение закрыто")

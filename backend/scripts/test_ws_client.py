
import asyncio
import websockets
import json
import sys
from datetime import datetime

def format_timestamp():
    return datetime.now().strftime("%H:%M:%S")

async def websocket_client(token):
    uri = f"ws://localhost:8000/api/v1/ws?token={token}"

    try:
        async with websockets.connect(uri) as websocket:
            print("=" * 70)
            print(f"✅ Подключено к WebSocket | {format_timestamp()}")
            print(f"🔗 URI: ws://localhost:8000/api/v1/ws")
            print("=" * 70)
            print()

            async def receive_messages():
                while True:
                    try:
                        message = await websocket.recv()
                        data = json.loads(message)

                        timestamp = format_timestamp()
                        msg_type = data.get('type', 'UNKNOWN')

                        if msg_type == 'CONNECTED':
                            print(f"[{timestamp}] 🟢 CONNECTED")
                            print(f"           User ID: {data.get('user_id')}")
                            print(f"           Message: {data.get('message')}")

                        elif msg_type == 'PONG':
                            print(f"[{timestamp}] 🏓 PONG")

                        elif msg_type == 'NEW_ORDER':
                            print(f"\n[{timestamp}] 📦 NEW_ORDER - Новый заказ доступен!")
                            order = data.get('data', {})
                            print(f"           Order ID: {order.get('order_id')}")
                            print(f"           Address: {order.get('pickup_address')}")
                            print(f"           Waste Type: {order.get('waste_type')}")
                            print(f"           Weight: {order.get('estimated_weight_kg')} kg")

                        elif msg_type == 'ORDER_ASSIGNED':
                            print(f"\n[{timestamp}] 👤 ORDER_ASSIGNED - Заказ принят курьером!")
                            order = data.get('data', {})
                            print(f"           Order ID: {order.get('order_id')}")
                            print(f"           Courier: {order.get('courier_name')}")
                            print(f"           Phone: {order.get('courier_phone')}")
                            print(f"           Rating: {order.get('courier_rating')}★")
                            print(f"           Message: {order.get('message')}")

                        elif msg_type == 'ORDER_STATUS_CHANGED':
                            print(f"\n[{timestamp}] 🔄 ORDER_STATUS_CHANGED")
                            order = data.get('data', {})
                            print(f"           Order ID: {order.get('order_id')}")
                            print(f"           Old Status: {order.get('old_status')}")
                            print(f"           New Status: {order.get('new_status')}")
                            print(f"           Message: {order.get('message')}")

                        elif msg_type == 'SHIFT_ENDED':
                            print(f"\n[{timestamp}] 👷 SHIFT_ENDED - Смена завершена!")
                            shift = data.get('data', {})
                            print(f"           Shift ID: {shift.get('shift_id')}")
                            print(f"           Duration: {shift.get('duration_hours')} часов")
                            print(f"           Orders Completed: {shift.get('orders_completed')}")
                            print(f"           Distance: {shift.get('total_distance_km')} км")
                            print(f"           Message: {shift.get('message')}")

                        elif msg_type == 'DAILY_STATS':
                            print(f"\n[{timestamp}] 📊 DAILY_STATS - Ежедневная статистика")
                            stats = data.get('data', {})
                            print(f"           Date: {stats.get('date')}")
                            print(f"           Total Hours: {stats.get('total_hours')} ч")
                            print(f"           Orders Completed: {stats.get('orders_completed')}")
                            print(f"           Distance: {stats.get('total_distance_km')} км")

                        elif msg_type == 'SHIFT_REMINDER':
                            print(f"\n[{timestamp}] ⏰ SHIFT_REMINDER - Напоминание о смене")
                            reminder = data.get('data', {})
                            print(f"           Message: {reminder.get('message')}")
                            print(f"           Shift Time: {reminder.get('shift_start_time')}")

                        elif msg_type == 'NEW_NOTIFICATION':
                            print(f"\n[{timestamp}] 🔔 NEW_NOTIFICATION")
                            notif = data.get('data', {})
                            print(f"           ID: {notif.get('id')}")
                            print(f"           Title: {notif.get('title')}")
                            print(f"           Message: {notif.get('message')}")
                            print(f"           Type: {notif.get('notification_type')}")

                        else:
                            print(f"\n[{timestamp}] 📨 {msg_type}")
                            print(f"           Data: {json.dumps(data, indent=11, ensure_ascii=False)}")

                        print("-" * 70)

                    except websockets.exceptions.ConnectionClosed:
                        print(f"\n[{format_timestamp()}] ❌ Соединение закрыто сервером")
                        break
                    except json.JSONDecodeError as e:
                        print(f"\n[{format_timestamp()}] ⚠️  Ошибка парсинга JSON: {e}")
                    except Exception as e:
                        print(f"\n[{format_timestamp()}] ⚠️  Ошибка: {e}")

            async def send_ping():
                await asyncio.sleep(2)
                while True:
                    try:
                        await websocket.send(json.dumps({"type": "PING"}))
                        print(f"[{format_timestamp()}] 📤 PING отправлен")
                        print("-" * 70)
                        await asyncio.sleep(30)
                    except websockets.exceptions.ConnectionClosed:
                        break
                    except Exception:
                        break

            await asyncio.gather(
                receive_messages(),
                send_ping()
            )

    except websockets.exceptions.InvalidURI:
        print("❌ Неправильный URI WebSocket")
    except ConnectionRefusedError:
        print("=" * 70)
        print("❌ Не удалось подключиться к серверу")
        print()
        print("🔍 Убедитесь что сервер запущен:")
        print("   cd /home/Maxim/PythonProjects/ecohaul-fixed/backend")
        print("   poetry run uvicorn app.main:app --reload")
        print("=" * 70)
    except Exception as e:
        error_msg = str(e)
        if "HTTP 403" in error_msg or "rejected WebSocket" in error_msg:
            print("=" * 70)
            print("❌ Ошибка подключения: HTTP 403 (Доступ запрещён)")
            print()
            print("🔍 Возможные причины:")
            print("   1. ✅ JWT токен истёк - получите новый через /auth/register или /auth/login")
            print("   2. ✅ Токен невалидный - проверьте что скопировали полностью")
            print("   3. ✅ Сервер запущен на порту 8000")
            print()
            print("💡 Как получить новый токен:")
            print('   curl -X POST http://localhost:8000/api/v1/auth/register \\')
            print('     -H "Content-Type: application/json" \\')
            print('     -d \'{"telegram_id": 123456789, "username": "test", "first_name": "Test", "role": "CLIENT"}\'')
            print("=" * 70)
        else:
            print(f"❌ Неожиданная ошибка: {e}")

def main():
    if len(sys.argv) < 2:
        print("=" * 70)
        print("❌ Ошибка: не указан JWT токен")
        print()
        print("📖 Использование:")
        print(f"   python3 {sys.argv[0]} YOUR_JWT_TOKEN")
        print()
        print("📝 Пример:")
        print(f"   python3 {sys.argv[0]} \"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...\"")
        print()
        print("💡 Как получить токен:")
        print("   1. Зарегистрируйтесь: POST /api/v1/auth/register")
        print("   2. Скопируйте access_token из ответа")
        print("=" * 70)
        sys.exit(1)

    token = sys.argv[1]

    print()
    print("🚀 Запуск WebSocket клиента...")
    print("   Нажмите Ctrl+C для выхода")
    print()

    try:
        asyncio.run(websocket_client(token))
    except KeyboardInterrupt:
        print()
        print("=" * 70)
        print(f"👋 Выход из WebSocket клиента | {format_timestamp()}")
        print("=" * 70)
        print()

if __name__ == "__main__":
    main()

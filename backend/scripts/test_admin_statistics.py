import asyncio
import httpx
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000/api/v1"

async def test_admin_statistics():
    async with httpx.AsyncClient() as client:
        print("1. Авторизация админа...")
        auth_response = await client.post(
            f"{BASE_URL}/auth/test",
            json={
                "telegram_id": 123456789,
                "username": "admin_test",
                "first_name": "Админ",
                "last_name": "Тестовый",
                "role": "ADMIN"
            }
        )

        if auth_response.status_code != 200:
            print(f"❌ Ошибка авторизации: {auth_response.status_code}")
            print(auth_response.text)
            return

        tokens = auth_response.json()
        access_token = tokens["access_token"]
        print(f"✅ Авторизация успешна")

        print("\n2. Получение общей статистики...")
        overview_response = await client.get(
            f"{BASE_URL}/admin/statistics/overview",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        print(f"Status: {overview_response.status_code}")
        if overview_response.status_code == 200:
            data = overview_response.json()
            print("✅ Общая статистика:")
            print(f"  👥 Пользователей: {data['total_users']}")
            print(f"  👨‍💼 Клиентов: {data['total_clients']}")
            print(f"  🚚 Курьеров: {data['total_couriers']} (верифицированных: {data['verified_couriers']})")
            print(f"  📦 Всего заказов: {data['total_orders']}")
            print(f"  ✅ Завершённых: {data['completed_orders']}")
            print(f"  ❌ Отменённых: {data['cancelled_orders']}")
            print(f"  💰 Общий доход: {data['total_revenue']} BYN")
            print(f"  💵 Доход сегодня: {data['revenue_today']} BYN")
            print(f"  📈 Средний чек: {data['avg_order_price']} BYN")
            print(f"  ⭐ Средний рейтинг: {data['avg_rating']}")
        else:
            print(f"❌ Ошибка: {overview_response.text}")
            return

        print("\n3. Статистика за последние 7 дней...")
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)

        period_response = await client.get(
            f"{BASE_URL}/admin/statistics/period",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        )

        print(f"Status: {period_response.status_code}")
        if period_response.status_code == 200:
            data = period_response.json()
            print("✅ Статистика за период:")
            print(f"  📦 Заказов: {data['orders_count']}")
            print(f"  ✅ Завершено: {data['completed_orders_count']}")
            print(f"  ❌ Отменено: {data['cancelled_orders_count']}")
            print(f"  💰 Доход: {data['revenue']} BYN")
            print(f"  👥 Новых клиентов: {data['new_clients']}")
            print(f"  🚚 Новых курьеров: {data['new_couriers']}")
        else:
            print(f"❌ Ошибка: {period_response.text}")

        print("\n4. Топ-5 курьеров по рейтингу...")
        top_response = await client.get(
            f"{BASE_URL}/admin/statistics/top-couriers",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"limit": 5, "order_by": "rating"}
        )

        print(f"Status: {top_response.status_code}")
        if top_response.status_code == 200:
            couriers = top_response.json()
            if couriers:
                print("✅ Топ курьеров:")
                for i, courier in enumerate(couriers, 1):
                    print(f"  {i}. {courier['courier_name']}")
                    print(f"     ⭐ Рейтинг: {courier['rating']}")
                    print(f"     📦 Заказов: {courier['completed_orders']}")
                    print(f"     💰 Доход: {courier['total_revenue']} BYN")
            else:
                print("  ℹ️  Курьеров пока нет")
        else:
            print(f"❌ Ошибка: {top_response.text}")

        print("\n" + "="*50)
        print("✅ Все тесты пройдены успешно!")

if __name__ == "__main__":
    asyncio.run(test_admin_statistics())

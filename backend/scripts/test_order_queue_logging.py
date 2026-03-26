import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from app.core.database import async_session_maker
from app.models.order import Order
from app.models.order_queue import OrderQueue
from app.models.user import User
from app.models.enums import OrderStatus, OrderQueueStatus, UserRole

async def test_order_queue_logging():

    async with async_session_maker() as db:
        stmt = select(User).where(User.role == UserRole.COURIER).limit(1)
        result = await db.execute(stmt)
        courier = result.scalar_one_or_none()

        if not courier:
            print("❌ Не найден курьер для теста")
            return

        print(f"✅ Найден курьер: {courier.full_name} (ID: {courier.id})")

        stmt = select(Order).where(Order.status == OrderStatus.PENDING).limit(1)
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()

        if not order:
            print("❌ Не найден заказ со статусом PENDING для теста")
            return

        print(f"✅ Найден заказ: {order.id} (статус: {order.status})")

        stmt = select(OrderQueue).where(OrderQueue.order_id == order.id)
        result = await db.execute(stmt)
        queue_entries_before = result.scalars().all()

        print(f"📊 Записей в OrderQueue до: {len(queue_entries_before)}")

        now = datetime.now(timezone.utc)
        order.courier_id = courier.id
        order.status = OrderStatus.ASSIGNED
        order.accepted_at = now

        queue_entry = OrderQueue(
            order_id=order.id,
            courier_id=courier.id,
            status=OrderQueueStatus.ACCEPTED,
            priority=order.priority,
            distance_km=0.0,
            offered_at=now,
            expires_at=now + timedelta(minutes=30),
            responded_at=now,
        )
        db.add(queue_entry)

        await db.commit()

        print(f"✅ Заказ {order.id} принят курьером {courier.id}")

        stmt = select(OrderQueue).where(
            OrderQueue.order_id == order.id,
            OrderQueue.courier_id == courier.id,
        )
        result = await db.execute(stmt)
        created_entry = result.scalar_one_or_none()

        if created_entry:
            print(f"✅ Запись в OrderQueue создана:")
            print(f"   - ID: {created_entry.id}")
            print(f"   - Order ID: {created_entry.order_id}")
            print(f"   - Courier ID: {created_entry.courier_id}")
            print(f"   - Status: {created_entry.status}")
            print(f"   - Priority: {created_entry.priority}")
            print(f"   - Distance: {created_entry.distance_km} км")
            print(f"   - Offered at: {created_entry.offered_at}")
            print(f"   - Responded at: {created_entry.responded_at}")
            print(f"   - Expires at: {created_entry.expires_at}")
            print(f"   - Response time: {created_entry.response_time_seconds} сек")
        else:
            print("❌ Запись в OrderQueue не создалась")

        stmt = select(OrderQueue).where(OrderQueue.order_id == order.id)
        result = await db.execute(stmt)
        queue_entries_after = result.scalars().all()

        print(f"📊 Записей в OrderQueue после: {len(queue_entries_after)}")

        await db.rollback()
        print("\n⚠️  Изменения откачены (тестовый режим)")

if __name__ == "__main__":
    print("🧪 Тестирование логирования OrderQueue при принятии заказов\n")
    asyncio.run(test_order_queue_logging())

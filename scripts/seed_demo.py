"""Seed synthetic portfolio data, only in a database named ecohaul_demo."""
import argparse
import asyncio
from datetime import datetime, timedelta, timezone
from getpass import getpass
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from sqlalchemy import select
from app.core.config import settings
from app.core.database import async_session_maker, engine
from app.core.security import hash_password
from app.models import Address, Order, User
from app.models.enums import CourierStatus, GarbageType, OrderStatus, UserRole


async def seed(password):
    if engine.url.database != 'ecohaul_demo':
        raise SystemExit('Refusing to seed: DATABASE_URL must point to ecohaul_demo')
    if settings.ENABLE_DEV_AUTH or settings.TELEGRAM_ENABLED:
        raise SystemExit('Disable dev authentication and Telegram before seeding demo data')
    try:
        async with async_session_maker() as db:
            if await db.scalar(select(User.id).limit(1)):
                raise SystemExit('Demo database is not empty; existing data was preserved')
            admin = User(telegram_id=-10001, first_name='Demo', last_name='Admin',
                         email='admin@example.test', password_hash=hash_password(password),
                         role=UserRole.ADMIN, is_active=True, is_verified=True)
            customer = User(telegram_id=-10002, first_name='Анна', last_name='Демонстрационная',
                            role=UserRole.CLIENT, is_active=True)
            courier = User(telegram_id=-10003, first_name='Алексей', last_name='Демонстрационный',
                           role=UserRole.COURIER, courier_status=CourierStatus.ACTIVE,
                           is_active=True, is_verified=True, total_orders=12, completed_orders=10)
            db.add_all([admin, customer, courier])
            await db.flush()
            address = Address(user_id=customer.id, latitude=53.9, longitude=27.56,
                              location='SRID=4326;POINT(27.56 53.9)', full_address='Минск, Аэродромная, 1',
                              city='Минск', district='Октябрьский', street='аэродромная', house_number='1')
            db.add(address)
            await db.flush()
            now = datetime.now(timezone.utc)
            for index, status in enumerate([OrderStatus.PENDING, OrderStatus.ASSIGNED,
                                            OrderStatus.IN_PROGRESS, OrderStatus.COMPLETED]):
                db.add(Order(client_id=customer.id, pickup_address_id=address.id,
                             courier_id=courier.id if status != OrderStatus.PENDING else None,
                             garbage_type=GarbageType.HOUSEHOLD, number_of_bags=index+1,
                             price_before_discount=(index+1)*2, discount_amount=0, final_price=(index+1)*2,
                             status=status, scheduled_time=now+timedelta(days=1),
                             expires_at=now+timedelta(minutes=30),
                             accepted_at=now if status != OrderStatus.PENDING else None,
                             completed_at=now if status == OrderStatus.COMPLETED else None,
                             description='Синтетические данные для демонстрации интерфейса'))
            await db.commit()
        print('Created synthetic demo data. Admin email: admin@example.test')
    finally:
        await engine.dispose()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--admin-password', help='Omit to enter the demo password interactively')
    args = parser.parse_args()
    password = args.admin_password or getpass('Demo admin password (12+ characters): ')
    if len(password) < 12:
        raise SystemExit('Use at least 12 characters')
    asyncio.run(seed(password))

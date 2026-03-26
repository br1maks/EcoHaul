
import asyncio
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.core.database import async_session_maker
from app.core.security import hash_password
from app.models.user import User
from app.models.enums import UserRole

async def create_admin(email: str, password: str, first_name: str, last_name: str):
    async with async_session_maker() as db:
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is not None:
            if existing.role == UserRole.ADMIN:
                print(f"Администратор с email {email} уже существует.")
                existing.password_hash = hash_password(password)
                await db.commit()
                print("Пароль обновлён.")
            else:
                existing.role = UserRole.ADMIN
                existing.email = email
                existing.password_hash = hash_password(password)
                await db.commit()
                print(f"Пользователь {existing.full_name} повышен до ADMIN.")
            return

        admin = User(
            telegram_id=-1,
            first_name=first_name,
            last_name=last_name,
            email=email,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True,
            is_telegram_verified=False,
        )
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        print(f"Администратор создан!")
        print(f"  ID:    {admin.id}")
        print(f"  Имя:   {admin.full_name}")
        print(f"  Email: {admin.email}")
        print(f"  Роль:  {admin.role}")

def main():
    parser = argparse.ArgumentParser(description="Создать администратора EcoHaul")
    parser.add_argument("--email", default="admin@ecohaul.ru", help="Email администратора")
    parser.add_argument("--password", help="Пароль (если не указан — спросит интерактивно)")
    parser.add_argument("--first-name", default="Admin", help="Имя")
    parser.add_argument("--last-name", default="EcoHaul", help="Фамилия")
    args = parser.parse_args()

    password = args.password
    if not password:
        import getpass
        password = getpass.getpass(f"Пароль для {args.email}: ")
        confirm = getpass.getpass("Повторите пароль: ")
        if password != confirm:
            print("Пароли не совпадают!")
            sys.exit(1)

    if len(password) < 6:
        print("Пароль должен быть не менее 6 символов!")
        sys.exit(1)

    asyncio.run(create_admin(args.email, password, args.first_name, args.last_name))

if __name__ == "__main__":
    main()

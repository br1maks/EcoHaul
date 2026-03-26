import logging
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from sqlalchemy import select
from app.core.config import settings
from app.core.database import async_session_maker
from app.models import User, UserRole

router = Router()
logger = logging.getLogger(__name__)

@router.message(CommandStart())
async def cmd_start(message: Message):
    if not message.from_user:
        return None

    telegram_id = message.from_user.id
    first_name = message.from_user.first_name or "Пользователь"
    greeting = f"Привет, {first_name}!"

    try:
        async with async_session_maker() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                user = User(
                    telegram_id=telegram_id,
                    first_name=first_name,
                    last_name=message.from_user.last_name or "",
                    telegram_username=message.from_user.username,
                    role=UserRole.CLIENT,
                    is_active=True,
                )
                session.add(user)
                await session.commit()
                greeting = f"Добро пожаловать, {first_name}! 🎉\nВы зарегистрированы как клиент."
            else:
                greeting = f"С возвращением, {first_name}!"
    except Exception as e:
        logger.error(f"Ошибка БД в /start для telegram_id={telegram_id}: {e}")

    buttons = [[
        InlineKeyboardButton(
            text="📦 Открыть приложение",
            web_app=WebAppInfo(url=settings.WEBAPP_URL)
        )
    ]]

    if user and user.role == UserRole.COURIER:
        buttons.append([
            InlineKeyboardButton(
                text="🚚 Панель курьера",
                web_app=WebAppInfo(url=f"{settings.WEBAPP_URL}/courier")
            )
        ])
    elif user and user.role == UserRole.ADMIN:
        buttons.append([
            InlineKeyboardButton(
                text="⚙️ Панель администратора",
                web_app=WebAppInfo(url=f"{settings.WEBAPP_URL}/admin")
            )
        ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(greeting, reply_markup=keyboard)

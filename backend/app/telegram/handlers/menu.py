import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from sqlalchemy import select
from app.core.config import settings
from app.core.database import async_session_maker
from app.models import User, UserRole

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("menu"))
async def cmd_menu(message: Message):
    if not message.from_user:
        return None

    telegram_id = message.from_user.id

    try:
        async with async_session_maker() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Ошибка БД в /menu для telegram_id={telegram_id}: {e}")
        user = None

    if user is None:
        await message.answer("Вы не зарегистрированы. Нажмите /start для начала работы.")
        return None

    if user.role == UserRole.COURIER:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏠 Панель курьера",
                    web_app=WebAppInfo(url=f"{settings.WEBAPP_URL}/courier")
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Доступные заказы",
                    web_app=WebAppInfo(url=f"{settings.WEBAPP_URL}/courier/orders")
                )
            ],
            [
                InlineKeyboardButton(
                    text="⏱ Смены",
                    web_app=WebAppInfo(url=f"{settings.WEBAPP_URL}/courier/shifts")
                )
            ],
            [
                InlineKeyboardButton(
                    text="👤 Профиль",
                    web_app=WebAppInfo(url=f"{settings.WEBAPP_URL}/courier/profile")
                )
            ],
        ])
        await message.answer(
            f"👋 Меню курьера, {user.first_name}!\n\nВыберите раздел:",
            reply_markup=keyboard
        )

    elif user.role == UserRole.ADMIN:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚙️ Панель администратора",
                    web_app=WebAppInfo(url=f"{settings.WEBAPP_URL}/admin")
                )
            ],
            [
                InlineKeyboardButton(
                    text="📦 Заказы",
                    web_app=WebAppInfo(url=f"{settings.WEBAPP_URL}/admin/orders")
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Аналитика",
                    web_app=WebAppInfo(url=f"{settings.WEBAPP_URL}/admin/analytics")
                )
            ],
        ])
        await message.answer(
            f"⚙️ Меню администратора, {user.first_name}!\n\nВыберите раздел:",
            reply_markup=keyboard
        )

    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📦 Открыть приложение",
                    web_app=WebAppInfo(url=settings.WEBAPP_URL)
                )
            ],
            [
                InlineKeyboardButton(
                    text="🆕 Новый заказ",
                    web_app=WebAppInfo(url=f"{settings.WEBAPP_URL}/new-order")
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Мои заказы",
                    web_app=WebAppInfo(url=f"{settings.WEBAPP_URL}/orders")
                )
            ],
        ])
        await message.answer(
            f"👋 Привет, {user.first_name}!\n\nВыберите раздел:",
            reply_markup=keyboard
        )

import asyncio
import logging
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from app.celery_app import celery_app
from app.core.config import settings

logger = logging.getLogger(__name__)

def _get_bot() -> Bot:
    return Bot(token=settings.BOT_TOKEN)

@celery_app.task(bind=True, max_retries=3)
def notify_user(self, telegram_id: int, text: str) -> None:
    if not settings.TELEGRAM_ENABLED:
        logger.debug("Telegram delivery disabled")
        return
    async def _send():
        bot = _get_bot()
        try:
            await bot.send_message(chat_id=telegram_id, text=text)
        finally:
            await bot.session.close()

    try:
        asyncio.run(_send())
        logger.info(f"Уведомление отправлено: telegram_id={telegram_id}")
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        logger.warning(f"Не удалось отправить telegram_id={telegram_id}: {exc}")
    except Exception as exc:
        logger.error(f"Ошибка отправки telegram_id={telegram_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)

@celery_app.task
def notify_order_created(client_telegram_id: int, order_id: str) -> None:
    notify_user.delay(
        client_telegram_id,
        f"Ваш заказ принят!\nИщем ближайшего курьера..."
    )

@celery_app.task
def notify_order_accepted(client_telegram_id: int, courier_name: str) -> None:
    notify_user.delay(
        client_telegram_id,
        f"Курьер {courier_name} едет к вам!"
    )

@celery_app.task
def notify_order_completed(client_telegram_id: int) -> None:
    notify_user.delay(
        client_telegram_id,
        f"Заказ выполнен! Спасибо что пользуетесь нашим приложением."
    )

@celery_app.task
def notify_application_approved(telegram_id: int) -> None:
    notify_user.delay(
        telegram_id,
        "Ваша заявка на курьера одобрена!\n"
        "Теперь вы можете принимать заказы."
    )

@celery_app.task
def notify_application_rejected(telegram_id: int, comment: str | None) -> None:
    text = "Ваша заявка на курьера отклонена."
    if comment:
        text += f"\nПричина: {comment}"
    notify_user.delay(telegram_id, text)

GARBAGE_TYPE_LABELS = {
    "HOUSEHOLD": "Бытовой",
    "CONSTRUCTION": "Строительный",
}

@celery_app.task
def notify_new_order_to_couriers(
    courier_telegram_ids: list[int],
    pickup_address: str,
    final_price: float,
    garbage_type: str,
    number_of_bags: int,
) -> None:
    garbage_label = GARBAGE_TYPE_LABELS.get(garbage_type, garbage_type)
    text = (
        f"Новый заказ!\n"
        f"Адрес: {pickup_address}\n"
        f"{garbage_label}, {number_of_bags} мешк.\n"
        f"Цена: {final_price} руб.\n\n"
        "Откройте приложение, чтобы принять заказ."
    )
    for telegram_id in courier_telegram_ids:
        notify_user.delay(telegram_id, text)

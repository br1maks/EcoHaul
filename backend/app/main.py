from contextlib import asynccontextmanager
import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.websocket import router as websocket_router
from app.core.config import settings
from app.core.database import engine
from app.core.logging_config import setup_logging
from aiogram.types import BotCommand, BotCommandScopeDefault
from app.telegram import bot, dp
from app.core.redis import init_redis, close_redis

setup_logging(
    log_level="DEBUG" if settings.DEBUG else "INFO",
    log_dir="logs"
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Запуск EcoHaul API...")
    logger.info(f"Текущая фаза: {settings.CURRENT_PHASE}")
    logger.info(f"Зона обслуживания: {', '.join(settings.current_phase_streets)}")
    logger.info(f"DEBUG режим: {settings.DEBUG}")

    await init_redis()
    logger.info("Redis подключён")

    await bot.set_my_commands([
        BotCommand(command="start", description="Начать работу"),
        BotCommand(command="menu", description="Открыть меню"),
    ], scope=BotCommandScopeDefault())
    logger.info("Команды бота зарегистрированы")

    bot_task = asyncio.create_task(dp.start_polling(bot))
    logger.info("Telegram бот запущен")

    yield

    bot_task.cancel()
    try:
        await bot_task
    except asyncio.CancelledError:
        pass
    await bot.session.close()
    logger.info("Telegram бот остановлен")

    await close_redis()
    logger.info("Redis отключён")

    logger.info("Остановка EcoHaul API...")
    await engine.dispose()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="API сервиса вывоза мусора EcoHaul для города Минск",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    openapi_url="/api/openapi.json" if settings.DEBUG else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
app.include_router(websocket_router, prefix="/api/v1")

@app.get("/", tags=["Здоровье"])
async def root():
    return {
        "message": "EcoHaul API работает",
        "version": "1.0.0",
        "docs": "/api/docs",
        "current_phase": settings.CURRENT_PHASE,
        "service_area": settings.current_phase_streets,
    }

@app.get("/health", tags=["Здоровье"])
async def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "phase": settings.CURRENT_PHASE,
    }

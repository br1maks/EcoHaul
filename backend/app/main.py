import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1 import api_router
from app.core.config import settings
from app.core.database import engine
from app.core.logging_config import setup_logging
from app.core.redis import close_redis, get_redis, init_redis
from app.websocket import router as websocket_router
from app.services.outbox_dispatcher import CHANNELS, dispatch_forever

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(log_level="DEBUG" if settings.DEBUG else "INFO", log_dir="logs")
    if len(settings.SECRET_KEY) < 32 or settings.SECRET_KEY.startswith(("changeme", "your_")):
        raise RuntimeError("Set SECRET_KEY to a randomly generated secret of at least 32 characters")
    await init_redis()
    bot = None
    bot_task = None
    outbox_tasks = []
    try:
        if settings.TELEGRAM_ENABLED:
            from aiogram.types import BotCommand, BotCommandScopeDefault
            from app.telegram import bot, dp

            await bot.set_my_commands(
                [BotCommand(command="start", description="Начать работу"),
                 BotCommand(command="menu", description="Открыть меню")],
                scope=BotCommandScopeDefault(),
            )
            bot_task = asyncio.create_task(dp.start_polling(bot))
        outbox_tasks = [asyncio.create_task(dispatch_forever(channel), name=f"outbox-{channel}")
                        for channel in CHANNELS]
        yield
    finally:
        for task in outbox_tasks:
            task.cancel()
        await asyncio.gather(*outbox_tasks, return_exceptions=True)
        if bot_task is not None:
            bot_task.cancel()
            try:
                await bot_task
            except asyncio.CancelledError:
                pass
        if bot is not None:
            await bot.session.close()
        await close_redis()
        await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    lifespan=lifespan,
    docs_url="/api/docs" if settings.DOCS_ENABLED else None,
    redoc_url="/api/redoc" if settings.DOCS_ENABLED else None,
    openapi_url="/api/openapi.json" if settings.DOCS_ENABLED else None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(websocket_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Health"])
async def root():
    return {
        "message": "EcoHaul API",
        "version": settings.VERSION,
        "docs": app.docs_url,
        "current_phase": settings.CURRENT_PHASE,
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Readiness reports actual database and Redis availability with bounded I/O."""
    checks = {"database": "unavailable", "redis": "unavailable"}
    try:
        async with asyncio.timeout(3):
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        checks["database"] = "connected"
    except Exception:
        logger.warning("Database readiness check failed")
    try:
        async with asyncio.timeout(3):
            await get_redis().ping()
        checks["redis"] = "connected"
    except Exception:
        logger.warning("Redis readiness check failed")
    healthy = all(value == "connected" for value in checks.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "healthy" if healthy else "unhealthy", **checks,
                 "phase": settings.CURRENT_PHASE},
    )

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine,
)

from app.core.config import settings
from sqlalchemy.pool import NullPool

# Celery tasks use asyncio.run() per invocation. Connections must not cross event loops.
pool_options = ({"poolclass": NullPool} if settings.DB_USE_NULL_POOL else {
    "pool_size": settings.DB_POOL_SIZE, "max_overflow": settings.DB_MAX_OVERFLOW,
})

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    future=True,
    pool_pre_ping=True,
    **pool_options,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db() -> None:
 
    from app.models.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def drop_db() -> None:
 
    from app.models.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

async def close_db() -> None:

    await engine.dispose()


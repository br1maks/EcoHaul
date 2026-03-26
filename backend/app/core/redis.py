import redis.asyncio as aioredis
from app.core.config import settings

redis_pool: aioredis.Redis | None = None

async def init_redis() -> None:
    global redis_pool
    redis_pool = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )

async def close_redis() -> None:
    global redis_pool
    if redis_pool:
        await redis_pool.aclose()
        redis_pool = None

def get_redis() -> aioredis.Redis:
    if redis_pool is None:
        raise RuntimeError("Redis не инициализирован")
    return redis_pool
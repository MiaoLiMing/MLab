import asyncio

from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import get_settings


async def enqueue_memory_extraction(user_id: str, content: str) -> None:
    """Enqueue without making chat availability depend on Redis."""

    settings = get_settings()
    try:
        async with asyncio.timeout(0.5):
            redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
            await redis.enqueue_job("extract_memory", user_id, content)
            await redis.aclose()
    except (OSError, TimeoutError):
        return

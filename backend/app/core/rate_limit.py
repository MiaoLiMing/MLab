import asyncio
from collections import defaultdict, deque
from time import monotonic, time

from redis.asyncio import Redis
from redis.exceptions import RedisError


class SlidingWindowLimiter:
    """Small-process limiter used for abuse protection on sensitive endpoints."""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()
        self._redis: Redis | None = None

    def enable_redis(self, redis_url: str) -> None:
        self._redis = Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=0.2,
            socket_timeout=0.2,
        )

    async def allow(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        if self._redis is not None:
            bucket = int(time() // window_seconds)
            redis_key = f"mlab:rate-limit:{bucket}:{key}"
            try:
                value = await self._redis.incr(redis_key)
                if value == 1:
                    await self._redis.expire(redis_key, window_seconds + 5)
                return value <= limit
            except RedisError:
                # Availability is more important than distributed limiting during a Redis incident.
                pass
        now = monotonic()
        cutoff = now - window_seconds
        async with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                return False
            events.append(now)
            return True

    async def reset(self) -> None:
        async with self._lock:
            self._events.clear()

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()


rate_limiter = SlidingWindowLimiter()

import time
import logging
from typing import Dict, List, Optional
from fastapi import Request, HTTPException, status, Depends
import redis.asyncio as aioredis

from app.core.config import settings
from app.models.models import User, UserRole
from app.core.dependencies import get_current_user

logger = logging.getLogger(__name__)

# Configurable Rate Limits per Role (requests per 60-second window)
# ADMIN: 0 (Unlimited)
ROLE_RATE_LIMITS = {
    UserRole.EMPLOYEE: 20,
    UserRole.MANAGER: 40,
    UserRole.ADMIN: 0,  # Unlimited
}

# Redis Connection Cache
_redis_client: Optional[aioredis.Redis] = None


async def get_redis_client() -> Optional[aioredis.Redis]:
    global _redis_client
    if _redis_client is None:
        try:
            client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            await client.ping()
            _redis_client = client
        except Exception:
            _redis_client = "unavailable"

    return _redis_client if _redis_client != "unavailable" else None



# In-memory fallback sliding window log for local development/testing without Redis
_inmemory_sliding_windows: Dict[str, List[float]] = {}


"""
ALGORITHM CHOICE & RATIONALE:
We choose the Sliding Window Log Algorithm backed by Redis Sorted Sets (ZSET) over Fixed Window Counter.

Why Sliding Window Log over Fixed Window Counter:
1. Fixed Window Counters suffer from boundary burst spikes (e.g. an Employee could send 20 requests at 00:59 
   and 20 requests at 01:01, effectively executing 40 requests in 2 seconds while staying within two adjacent fixed windows).
2. Sliding Window Log maintains exact request timestamps in a Redis ZSET, automatically pruning timestamps 
   older than (now - 60s). This guarantees strict, smooth, boundary-free enforcement across any 60-second sliding interval.
3. It allows exact calculation of the oldest timestamp in the sliding window to return an accurate 'Retry-After' header.
"""


class RateLimiter:
    def __init__(self, endpoint_name: str, custom_limit: Optional[int] = None, window_seconds: int = 60):
        self.endpoint_name = endpoint_name
        self.custom_limit = custom_limit
        self.window_seconds = window_seconds

    async def __call__(self, request: Request, current_user: User = Depends(get_current_user)):
        # Rule 1: Admins are exempt from rate limiting (Unlimited)
        if current_user.role == UserRole.ADMIN:
            return

        # Determine limit for user role
        limit = self.custom_limit if self.custom_limit is not None else ROLE_RATE_LIMITS.get(current_user.role, 20)
        if limit <= 0:
            return  # Unlimited

        now = time.time()
        window_start = now - self.window_seconds
        rate_key = f"ratelimit:{self.endpoint_name}:{current_user.org_id}:{current_user.id}"

        redis_client = await get_redis_client()

        if redis_client is not None:
            try:
                # Use Redis Sorted Set (ZSET) for atomic sliding window log
                pipe = redis_client.pipeline()
                # 1. Remove timestamps older than window_start
                pipe.zremrangebyscore(rate_key, 0, window_start)
                # 2. Get current request count in sliding window
                pipe.zcard(rate_key)
                # 3. Get oldest timestamp in window (for precise Retry-After calculation)
                pipe.zrange(rate_key, 0, 0, withscores=True)
                
                results = await pipe.execute()
                current_count = results[1]
                oldest_entry = results[2]

                if current_count >= limit:
                    oldest_ts = oldest_entry[0][1] if oldest_entry else window_start
                    retry_after = max(1, int(self.window_seconds - (now - oldest_ts)))
                    
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Rate limit exceeded. You can send up to {limit} requests per minute. Try again in {retry_after} seconds.",
                        headers={"Retry-After": str(retry_after)}
                    )

                # Add current request timestamp to ZSET & set TTL
                pipe = redis_client.pipeline()
                pipe.zadd(rate_key, {str(now): now})
                pipe.expire(rate_key, self.window_seconds + 5)
                await pipe.execute()

                return

            except HTTPException:
                raise
            except Exception as e:
                global _redis_client
                _redis_client = "unavailable"
                logger.warning(f"Redis rate limiting failed ({e}). Falling back to in-memory sliding window.")


        # In-memory sliding window fallback (if Redis unavailable)
        timestamps = _inmemory_sliding_windows.get(rate_key, [])
        # Prune old timestamps
        timestamps = [ts for ts in timestamps if ts > window_start]

        if len(timestamps) >= limit:
            oldest_ts = timestamps[0] if timestamps else window_start
            retry_after = max(1, int(self.window_seconds - (now - oldest_ts)))
            _inmemory_sliding_windows[rate_key] = timestamps
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. You can send up to {limit} requests per minute. Try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)}
            )

        timestamps.append(now)
        _inmemory_sliding_windows[rate_key] = timestamps

import redis.asyncio as redis
from app.config import settings

# Redis client
# Note: decode_responses=True ensures we get strings back, not bytes
redis_client = redis.from_url(
    "redis://redis:6379/0", 
    encoding="utf-8", 
    decode_responses=True
)

async def get_cached_user(user_id: int):
    """Try to get user from cache."""
    try:
        key = f"user:{user_id}"
        data = await redis_client.hgetall(key)
        if data:
            return data
        return None
    except Exception:
        # Fail open: if Redis is down, return None and hit DB
        return None


async def cache_user(user_id: int, user_data: dict, expire_seconds: int = 300):
    """Cache user data for 5 minutes."""
    try:
        key = f"user:{user_id}"
        await redis_client.hset(key, mapping=user_data)
        await redis_client.expire(key, expire_seconds)
    except Exception:
        # Silently fail if Redis is unavailable
        pass
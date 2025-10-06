"""Redis connection and utility functions."""
import json
import logging
from typing import Any
from urllib.parse import urlparse

import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global Redis connection pool
redis_client: Redis | None = None


async def init_redis() -> Redis:
    """Initialize Redis connection."""
    global redis_client

    try:
        # Parse Redis URL
        parsed_url = urlparse(str(settings.REDIS_URL))
        
        # Extract connection parameters with fallbacks
        host = parsed_url.hostname or "redis"
        port = parsed_url.port or 6379
        password = parsed_url.password
        db = int(parsed_url.path.lstrip("/")) if parsed_url.path and parsed_url.path != "/" else 0
        
    except (ValueError, AttributeError) as e:
        logger.warning(f"Failed to parse REDIS_URL: {e}. Using fallback configuration.")
        # Fallback to individual environment variables or defaults
        host = getattr(settings, 'REDIS_HOST', 'redis')
        port = getattr(settings, 'REDIS_PORT', 6379)
        password = getattr(settings, 'REDIS_PASSWORD', None)
        db = getattr(settings, 'REDIS_DB', 0)

    redis_client = redis.Redis(
        host=host,
        port=int(port),
        db=int(db),
        password=password,
        encoding="utf-8",
        decode_responses=True,
        socket_keepalive=True,
        socket_keepalive_options={},
        health_check_interval=30,
    )

    # Test connection
    try:
        await redis_client.ping()
        logger.info("Redis connection established successfully")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise

    return redis_client


async def get_redis() -> Redis:
    """Get Redis client instance."""
    if not redis_client:
        await init_redis()
    return redis_client


async def close_redis() -> None:
    """Close Redis connection."""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None
        logger.info("Redis connection closed")


class RedisCache:
    """Redis cache utility class."""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def get(self, key: str) -> str | None:
        """Get value from cache."""
        try:
            return await self.redis.get(key)
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: str,
        ttl: int | None = None
    ) -> bool:
        """Set value in cache with optional TTL."""
        try:
            if ttl:
                return await self.redis.setex(key, ttl, value)
            else:
                return await self.redis.set(key, value)
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False

    async def get_json(self, key: str) -> dict[str, Any] | None:
        """Get JSON value from cache."""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error for key {key}: {e}")
                return None
        return None

    async def set_json(
        self,
        key: str,
        value: dict[str, Any],
        ttl: int | None = None
    ) -> bool:
        """Set JSON value in cache with optional TTL."""
        try:
            json_value = json.dumps(value)
            return await self.set(key, json_value, ttl)
        except Exception as e:
            logger.error(f"JSON encode error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration for key."""
        try:
            return await self.redis.expire(key, ttl)
        except Exception as e:
            logger.error(f"Redis EXPIRE error for key {key}: {e}")
            return False


class RedisRateLimiter:
    """Redis-based rate limiter."""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window: int,
        identifier: str = "default"
    ) -> tuple[bool, dict[str, int]]:
        """
        Check if request is allowed within rate limit.

        Args:
            key: Base key for rate limiting (e.g., "api_key:12345")
            limit: Number of requests allowed
            window: Time window in seconds
            identifier: Additional identifier (e.g., "per_minute", "per_hour")

        Returns:
            tuple: (is_allowed, {"remaining": int, "reset_time": int})
        """
        rate_key = f"rate_limit:{key}:{identifier}"

        try:
            # Use sliding window rate limiting
            current_time = await self.redis.time()
            current_timestamp = current_time[0]  # Unix timestamp

            # Remove old entries outside the window
            cutoff = current_timestamp - window
            await self.redis.zremrangebyscore(rate_key, 0, cutoff)

            # Count current requests
            current_count = await self.redis.zcard(rate_key)

            if current_count >= limit:
                # Get the oldest entry to calculate reset time
                oldest_entries = await self.redis.zrange(rate_key, 0, 0, withscores=True)
                reset_time = int(oldest_entries[0][1] + window) if oldest_entries else current_timestamp + window

                return False, {
                    "remaining": 0,
                    "reset_time": reset_time,
                    "limit": limit,
                    "window": window
                }

            # Add current request
            await self.redis.zadd(rate_key, {str(current_timestamp): current_timestamp})
            await self.redis.expire(rate_key, window)

            remaining = limit - current_count - 1
            reset_time = current_timestamp + window

            return True, {
                "remaining": remaining,
                "reset_time": reset_time,
                "limit": limit,
                "window": window
            }

        except Exception as e:
            logger.error(f"Rate limiting error for key {rate_key}: {e}")
            # On error, allow the request but log the issue
            return True, {
                "remaining": limit - 1,
                "reset_time": 0,
                "limit": limit,
                "window": window
            }


class RedisQueue:
    """Redis-based job queue."""

    def __init__(self, redis_client: Redis, queue_name: str = "scraping_queue"):
        self.redis = redis_client
        self.queue_name = queue_name
        self.processing_queue = f"{queue_name}:processing"

    async def enqueue(self, job_id: str, priority: int = 0) -> bool:
        """Add job to queue with priority."""
        try:
            # Use sorted set for priority queue (higher score = higher priority)
            result = await self.redis.zadd(self.queue_name, {job_id: priority})
            return result > 0
        except Exception as e:
            logger.error(f"Queue enqueue error for job {job_id}: {e}")
            return False

    async def dequeue(self, timeout: int = 10) -> str | None:
        """Get next job from queue (blocking)."""
        try:
            # Get highest priority job
            result = await self.redis.bzpopmax(self.queue_name, timeout=timeout)
            if result:
                _queue_name, job_id, priority = result
                # Move to processing queue
                await self.redis.zadd(self.processing_queue, {job_id: priority})
                return job_id
            return None
        except Exception as e:
            logger.error(f"Queue dequeue error: {e}")
            return None

    async def complete_job(self, job_id: str) -> bool:
        """Mark job as completed and remove from processing queue."""
        try:
            result = await self.redis.zrem(self.processing_queue, job_id)
            return result > 0
        except Exception as e:
            logger.error(f"Queue complete error for job {job_id}: {e}")
            return False

    async def retry_job(self, job_id: str, priority: int = 0) -> bool:
        """Move job from processing back to main queue for retry."""
        try:
            # Remove from processing and add back to main queue
            await self.redis.zrem(self.processing_queue, job_id)
            result = await self.redis.zadd(self.queue_name, {job_id: priority})
            return result > 0
        except Exception as e:
            logger.error(f"Queue retry error for job {job_id}: {e}")
            return False

    async def get_queue_stats(self) -> dict[str, int]:
        """Get queue statistics."""
        try:
            pending = await self.redis.zcard(self.queue_name)
            processing = await self.redis.zcard(self.processing_queue)

            return {
                "pending": pending,
                "processing": processing,
                "total": pending + processing
            }
        except Exception as e:
            logger.error(f"Queue stats error: {e}")
            return {"pending": 0, "processing": 0, "total": 0}


# Utility functions
async def cache_job_result(job_id: str, result_data: dict[str, Any], ttl: int | None = None) -> bool:
    """Cache job result."""
    redis_instance = await get_redis()
    cache = RedisCache(redis_instance)
    cache_key = f"job_result:{job_id}"
    return await cache.set_json(cache_key, result_data, ttl or settings.RESULT_CACHE_TTL)


async def get_cached_job_result(job_id: str) -> dict[str, Any] | None:
    """Get cached job result."""
    redis_instance = await get_redis()
    cache = RedisCache(redis_instance)
    cache_key = f"job_result:{job_id}"
    return await cache.get_json(cache_key)


async def cache_url_result(url: str, result_data: dict[str, Any], ttl: int | None = None) -> bool:
    """Cache result by URL hash."""
    import hashlib
    url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
    redis_instance = await get_redis()
    cache = RedisCache(redis_instance)
    cache_key = f"url_cache:{url_hash}"
    return await cache.set_json(cache_key, result_data, ttl or settings.CACHE_TTL)


async def get_cached_url_result(url: str) -> dict[str, Any] | None:
    """Get cached result by URL hash."""
    import hashlib
    url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
    redis_instance = await get_redis()
    cache = RedisCache(redis_instance)
    cache_key = f"url_cache:{url_hash}"
    return await cache.get_json(cache_key)

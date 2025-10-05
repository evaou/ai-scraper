"""
Redis connection pool with caching, rate limiting, and queue utilities.

This module provides async Redis client with connection pooling and helper functions
for caching, rate limiting, job queue management, and job status tracking.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any

import redis.asyncio as redis
from redis.asyncio import ConnectionPool

from .config import get_settings

logger = logging.getLogger(__name__)

# Global Redis client and connection pool
_redis_client: redis.Redis | None = None
_connection_pool: ConnectionPool | None = None


def create_redis_pool() -> ConnectionPool:
    """Create Redis connection pool with configuration."""
    settings = get_settings()

    return ConnectionPool.from_url(
        str(settings.REDIS_URL),
        encoding="utf-8",
        decode_responses=True,
        max_connections=settings.REDIS_POOL_MAX_CONNECTIONS,
        retry_on_timeout=True,
        health_check_interval=30,
    )


def get_redis_client() -> redis.Redis:
    """Get Redis client with connection pooling."""
    global _redis_client, _connection_pool

    if _redis_client is None:
        if _connection_pool is None:
            _connection_pool = create_redis_pool()

        _redis_client = redis.Redis(
            connection_pool=_connection_pool,
            socket_keepalive=True,
            socket_keepalive_options={},
        )
        logger.info("Redis client created with connection pooling")

    return _redis_client


# FastAPI dependency for Redis client
async def get_redis() -> redis.Redis:
    """FastAPI dependency that provides Redis client."""
    return get_redis_client()


# Cache helper functions
async def cache_get(key: str) -> str | None:
    """Get value from Redis cache."""
    try:
        client = get_redis_client()
        return await client.get(key)
    except Exception as e:
        logger.error(f"Cache get error for key {key}: {e}")
        return None


async def cache_set(key: str, value: str, ttl: int | None = None) -> bool:
    """Set value in Redis cache with optional TTL."""
    try:
        client = get_redis_client()
        if ttl:
            return await client.setex(key, ttl, value)
        else:
            return await client.set(key, value)
    except Exception as e:
        logger.error(f"Cache set error for key {key}: {e}")
        return False


async def cache_delete(key: str) -> bool:
    """Delete key from Redis cache."""
    try:
        client = get_redis_client()
        return bool(await client.delete(key))
    except Exception as e:
        logger.error(f"Cache delete error for key {key}: {e}")
        return False


# URL caching functions
def generate_url_cache_key(url: str, selector: str | None = None, options: dict | None = None) -> str:
    """Generate cache key for URL scraping results."""
    cache_data = {
        "url": url,
        "selector": selector or "",
        "options": options or {}
    }
    cache_str = json.dumps(cache_data, sort_keys=True)
    url_hash = hashlib.sha256(cache_str.encode()).hexdigest()[:16]
    return f"cache:url:{url_hash}"


async def get_cached_scrape_result(url: str, selector: str | None = None, options: dict | None = None) -> dict | None:
    """Get cached scraping result."""
    key = generate_url_cache_key(url, selector, options)
    cached = await cache_get(key)
    if cached:
        try:
            return json.loads(cached)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in cache key {key}")
            await cache_delete(key)
    return None


async def set_cached_scrape_result(url: str, result: dict, selector: str | None = None, options: dict | None = None) -> bool:
    """Cache scraping result with TTL."""
    settings = get_settings()
    key = generate_url_cache_key(url, selector, options)
    try:
        return await cache_set(key, json.dumps(result), ttl=settings.CACHE_TTL)
    except Exception as e:
        logger.error(f"Failed to cache scrape result: {e}")
        return False


# Rate limiting functions
async def rate_limit_check(identifier: str, limit: int, window_seconds: int = 60) -> dict[str, Any]:
    """
    Check rate limit for identifier using sliding window.

    Args:
        identifier: Rate limit identifier (IP, API key, etc.)
        limit: Maximum requests allowed in window
        window_seconds: Time window in seconds

    Returns:
        Dict with allowed status, current count, and reset time
    """
    try:
        client = get_redis_client()
        now = datetime.utcnow()
        now - timedelta(seconds=window_seconds)

        # Use minute-based key for simplicity
        minute_key = f"rate_limit:{identifier}:{now.strftime('%Y-%m-%d-%H-%M')}"

        # Get current count and increment
        current_count = await client.incr(minute_key)

        # Set expiration on first increment
        if current_count == 1:
            await client.expire(minute_key, window_seconds)

        allowed = current_count <= limit
        reset_time = now + timedelta(seconds=window_seconds)

        return {
            "allowed": allowed,
            "current_count": current_count,
            "limit": limit,
            "reset_time": reset_time.isoformat(),
            "window_seconds": window_seconds,
        }

    except Exception as e:
        logger.error(f"Rate limit check error for {identifier}: {e}")
        # Allow on error to prevent blocking service
        return {
            "allowed": True,
            "current_count": 0,
            "limit": limit,
            "error": str(e),
        }


# Job queue functions
async def enqueue_job(job_id: str, priority: int = 0) -> bool:
    """Add job to processing queue."""
    try:
        client = get_redis_client()
        queue_key = "job_queue"

        # Use sorted set for priority queue (lower score = higher priority)
        score = priority
        return bool(await client.zadd(queue_key, {job_id: score}))
    except Exception as e:
        logger.error(f"Failed to enqueue job {job_id}: {e}")
        return False


async def dequeue_job(timeout: int = 5) -> str | None:
    """Get next job from queue (blocking)."""
    try:
        client = get_redis_client()
        queue_key = "job_queue"

        # Use BZPOPMIN for blocking pop with lowest score (highest priority)
        result = await client.bzpopmin(queue_key, timeout=timeout)
        if result:
            return result[1]  # Return job_id (result is (key, job_id, score))
        return None
    except Exception as e:
        logger.error(f"Failed to dequeue job: {e}")
        return None


async def get_queue_size() -> int:
    """Get current job queue size."""
    try:
        client = get_redis_client()
        return await client.zcard("job_queue")
    except Exception as e:
        logger.error(f"Failed to get queue size: {e}")
        return 0


# Job status functions
async def set_job_status(job_id: str, status: str, data: dict | None = None) -> bool:
    """Set job status with optional data."""
    try:
        settings = get_settings()
        get_redis_client()
        key = f"job_status:{job_id}"

        status_data = {
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data or {}
        }

        return await cache_set(key, json.dumps(status_data), ttl=settings.JOB_STATUS_TTL)
    except Exception as e:
        logger.error(f"Failed to set job status for {job_id}: {e}")
        return False


async def get_job_status(job_id: str) -> dict | None:
    """Get job status and data."""
    try:
        key = f"job_status:{job_id}"
        cached = await cache_get(key)
        if cached:
            return json.loads(cached)
        return None
    except Exception as e:
        logger.error(f"Failed to get job status for {job_id}: {e}")
        return None


async def delete_job_status(job_id: str) -> bool:
    """Delete job status from cache."""
    try:
        key = f"job_status:{job_id}"
        return await cache_delete(key)
    except Exception as e:
        logger.error(f"Failed to delete job status for {job_id}: {e}")
        return False


# Health check and monitoring functions
async def check_redis_health() -> dict[str, Any]:
    """Check Redis connectivity and return health status."""
    try:
        client = get_redis_client()

        # Test basic connectivity
        await client.ping()

        # Get Redis info
        info = await client.info()

        return {
            "status": "healthy",
            "connected": True,
            "redis_version": info.get("redis_version"),
            "connected_clients": info.get("connected_clients", 0),
            "used_memory": info.get("used_memory", 0),
            "used_memory_human": info.get("used_memory_human", "0B"),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {
            "status": "unhealthy",
            "connected": False,
            "error": str(e),
        }


async def close_redis() -> None:
    """Close Redis connections and cleanup."""
    global _redis_client, _connection_pool

    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis client closed")

    if _connection_pool is not None:
        await _connection_pool.disconnect()
        _connection_pool = None
        logger.info("Redis connection pool closed")

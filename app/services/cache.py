"""
Caching service for web scraping results.

This module provides high-level caching functionality for scraping results,
including URL-based caching, cache invalidation, and cache statistics.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from app.core.cache import (
    cache_delete,
    cache_get,
    get_cached_scrape_result,
    get_redis_client,
    set_cached_scrape_result,
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class CacheService:
    """High-level caching service for scraping results."""

    def __init__(self):
        self.settings = get_settings()
        self.redis = get_redis_client()

    async def get_scrape_result(
        self,
        url: str,
        selector: str | None = None,
        options: dict | None = None
    ) -> dict[str, Any] | None:
        """
        Get cached scraping result if available.

        Args:
            url: Target URL
            selector: CSS selector (if any)
            options: Scraping options

        Returns:
            Cached result or None if not found/expired
        """
        try:
            cached_result = await get_cached_scrape_result(url, selector, options)
            if cached_result:
                logger.debug(f"Cache hit for URL: {url}")
                # Update access statistics
                await self._update_cache_stats("hit")
                return cached_result
            else:
                logger.debug(f"Cache miss for URL: {url}")
                await self._update_cache_stats("miss")
                return None
        except Exception as e:
            logger.error(f"Error retrieving cached result: {e}")
            await self._update_cache_stats("error")
            return None

    async def store_scrape_result(
        self,
        url: str,
        result: dict[str, Any],
        selector: str | None = None,
        options: dict | None = None,
        custom_ttl: int | None = None
    ) -> bool:
        """
        Store scraping result in cache.

        Args:
            url: Target URL
            result: Scraping result data
            selector: CSS selector (if any)
            options: Scraping options
            custom_ttl: Custom TTL override

        Returns:
            True if stored successfully, False otherwise
        """
        try:
            # Add metadata to cached result
            enriched_result = {
                **result,
                "cached_at": datetime.utcnow().isoformat(),
                "cache_ttl": custom_ttl or self.settings.CACHE_TTL,
                "cache_key_info": {
                    "url": url,
                    "selector": selector,
                    "options": options or {}
                }
            }

            success = await set_cached_scrape_result(url, enriched_result, selector, options)
            if success:
                logger.debug(f"Cached result for URL: {url}")
                await self._update_cache_stats("store")
            return success
        except Exception as e:
            logger.error(f"Error storing cached result: {e}")
            await self._update_cache_stats("store_error")
            return False

    async def invalidate_url(self, url: str, selector: str | None = None, options: dict | None = None) -> bool:
        """
        Invalidate cached result for a specific URL.

        Args:
            url: Target URL
            selector: CSS selector (if any)
            options: Scraping options

        Returns:
            True if invalidated successfully
        """
        try:
            from app.core.cache import generate_url_cache_key
            cache_key = generate_url_cache_key(url, selector, options)
            success = await cache_delete(cache_key)
            if success:
                logger.info(f"Invalidated cache for URL: {url}")
                await self._update_cache_stats("invalidate")
            return success
        except Exception as e:
            logger.error(f"Error invalidating cache for URL {url}: {e}")
            return False

    async def invalidate_pattern(self, url_pattern: str) -> int:
        """
        Invalidate cached results matching a URL pattern.

        Args:
            url_pattern: URL pattern (supports wildcards)

        Returns:
            Number of keys invalidated
        """
        try:
            # Get all cache keys matching pattern
            pattern = f"cache:url:*{url_pattern}*" if "*" not in url_pattern else f"cache:url:{url_pattern}"
            keys = await self.redis.keys(pattern)

            if keys:
                deleted_count = await self.redis.delete(*keys)
                logger.info(f"Invalidated {deleted_count} cache entries for pattern: {url_pattern}")
                await self._update_cache_stats("bulk_invalidate", deleted_count)
                return deleted_count
            return 0
        except Exception as e:
            logger.error(f"Error invalidating cache pattern {url_pattern}: {e}")
            return 0

    async def get_cache_info(self, url: str, selector: str | None = None, options: dict | None = None) -> dict[str, Any] | None:
        """
        Get cache information for a specific URL.

        Args:
            url: Target URL
            selector: CSS selector (if any)
            options: Scraping options

        Returns:
            Cache information or None if not cached
        """
        try:
            from app.core.cache import generate_url_cache_key
            cache_key = generate_url_cache_key(url, selector, options)

            # Check if key exists and get TTL
            exists = await self.redis.exists(cache_key)
            if not exists:
                return None

            ttl = await self.redis.ttl(cache_key)
            cached_data = await cache_get(cache_key)

            if cached_data:
                try:
                    data = json.loads(cached_data)
                    cached_at = data.get("cached_at")
                    cache_ttl = data.get("cache_ttl", self.settings.CACHE_TTL)

                    return {
                        "cache_key": cache_key,
                        "exists": True,
                        "cached_at": cached_at,
                        "ttl_seconds": ttl,
                        "original_ttl": cache_ttl,
                        "expires_at": (
                            datetime.fromisoformat(cached_at) + timedelta(seconds=cache_ttl)
                        ).isoformat() if cached_at else None,
                        "size_bytes": len(cached_data)
                    }
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in cache key {cache_key}")
                    return {"cache_key": cache_key, "exists": True, "error": "Invalid JSON"}

            return {"cache_key": cache_key, "exists": False}
        except Exception as e:
            logger.error(f"Error getting cache info for {url}: {e}")
            return None

    async def get_cache_statistics(self) -> dict[str, Any]:
        """
        Get comprehensive cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        try:
            # Get all cache-related keys
            cache_keys = await self.redis.keys("cache:*")
            await self.redis.keys("cache_stats:*")

            # Basic counts
            total_cached_items = len([k for k in cache_keys if k.startswith("cache:url:")])

            # Memory usage estimation
            total_memory = 0
            for key in cache_keys[:100]:  # Sample first 100 keys for performance
                try:
                    memory = await self.redis.memory_usage(key)
                    if memory:
                        total_memory += memory
                except Exception:
                    pass  # Key might have expired

            # Estimate total memory usage
            if cache_keys and total_cached_items > 0:
                avg_memory_per_key = total_memory / min(len(cache_keys), 100)
                estimated_total_memory = avg_memory_per_key * total_cached_items
            else:
                estimated_total_memory = 0

            # Get hit/miss statistics
            hit_count = await self._get_cache_stat("hit") or 0
            miss_count = await self._get_cache_stat("miss") or 0
            total_requests = hit_count + miss_count
            hit_rate = (hit_count / total_requests * 100) if total_requests > 0 else 0

            return {
                "total_cached_items": total_cached_items,
                "cache_hit_count": hit_count,
                "cache_miss_count": miss_count,
                "cache_hit_rate_percent": round(hit_rate, 2),
                "total_cache_requests": total_requests,
                "estimated_memory_bytes": int(estimated_total_memory),
                "estimated_memory_mb": round(estimated_total_memory / 1024 / 1024, 2),
                "store_count": await self._get_cache_stat("store") or 0,
                "invalidate_count": await self._get_cache_stat("invalidate") or 0,
                "error_count": await self._get_cache_stat("error") or 0,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting cache statistics: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    async def clear_cache(self, pattern: str = "cache:url:*") -> int:
        """
        Clear cache entries matching pattern.

        Args:
            pattern: Redis key pattern to clear

        Returns:
            Number of keys deleted
        """
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                deleted_count = await self.redis.delete(*keys)
                logger.info(f"Cleared {deleted_count} cache entries matching pattern: {pattern}")
                await self._update_cache_stats("clear", deleted_count)
                return deleted_count
            return 0
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return 0

    async def _update_cache_stats(self, stat_type: str, count: int = 1) -> None:
        """Update cache statistics counters."""
        try:
            key = f"cache_stats:{stat_type}"
            await self.redis.incr(key, count)
            await self.redis.expire(key, 86400)  # Expire stats after 24 hours
        except Exception as e:
            logger.debug(f"Error updating cache stats: {e}")

    async def _get_cache_stat(self, stat_type: str) -> int | None:
        """Get cache statistic value."""
        try:
            key = f"cache_stats:{stat_type}"
            value = await self.redis.get(key)
            return int(value) if value else None
        except Exception:
            return None


# Global cache service instance
_cache_service: CacheService | None = None


def get_cache_service() -> CacheService:
    """Get global cache service instance."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service

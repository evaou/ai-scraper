"""Admin API routes for system management."""
import logging
from datetime import datetime

import psutil
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_optional_api_key
from app.core.database import get_db
from app.core.redis import RedisQueue, get_redis
from app.crud.job import job_crud
from app.models.api_key import ApiKey
from app.schemas.scraping import (
    AdminStatsResponse,
    JobStatsResponse,
    QueueStatsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/admin/stats",
    response_model=AdminStatsResponse,
    summary="Get system statistics",
    description="Get comprehensive system statistics including jobs, queue, cache, and system metrics"
)
async def get_admin_stats(
    db: AsyncSession = Depends(get_db),
    api_key: ApiKey | None = Depends(get_optional_api_key),
) -> AdminStatsResponse:
    """
    Get comprehensive system statistics.

    Includes job statistics, queue status, cache metrics, and system information.
    """
    try:
        # Get job statistics
        api_key_id = api_key.id if api_key else None
        job_stats_data = await job_crud.get_job_stats(db, api_key_id=api_key_id)

        job_stats = JobStatsResponse(
            total=job_stats_data["total"],
            pending=job_stats_data["pending"],
            running=job_stats_data["running"],
            completed=job_stats_data["completed"],
            failed=job_stats_data["failed"],
            cancelled=job_stats_data["cancelled"],
            retrying=job_stats_data["retrying"],
            average_execution_time=job_stats_data["average_execution_time"],
        )

        # Get queue statistics
        redis_client = await get_redis()
        queue = RedisQueue(redis_client)
        queue_stats_data = await queue.get_queue_stats()

        queue_stats = QueueStatsResponse(
            pending=queue_stats_data["pending"],
            processing=queue_stats_data["processing"],
            total=queue_stats_data["total"],
            workers=1,  # This would be dynamic in a real implementation
        )

        # Get cache statistics
        cache_stats = {}
        try:
            cache_info = await redis_client.info("memory")
            cache_stats = {
                "used_memory": cache_info.get("used_memory", 0),
                "used_memory_human": cache_info.get("used_memory_human", "0B"),
                "connected_clients": cache_info.get("connected_clients", 0),
                "total_commands_processed": cache_info.get("total_commands_processed", 0),
            }
        except Exception as e:
            logger.warning(f"Could not get cache stats: {e}")
            cache_stats = {"error": "Cache statistics unavailable"}

        # Get system statistics
        system_stats = {}
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()

            # Disk usage
            disk = psutil.disk_usage("/")

            system_stats = {
                "cpu_percent": cpu_percent,
                "memory_total": memory.total,
                "memory_available": memory.available,
                "memory_percent": memory.percent,
                "disk_total": disk.total,
                "disk_free": disk.free,
                "disk_percent": (disk.total - disk.free) / disk.total * 100,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.warning(f"Could not get system stats: {e}")
            system_stats = {"error": "System statistics unavailable"}

        return AdminStatsResponse(
            jobs=job_stats,
            queue=queue_stats,
            cache=cache_stats,
            system=system_stats,
        )

    except Exception as e:
        logger.error(f"Error getting admin stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system statistics"
        )


@router.post(
    "/admin/cleanup",
    summary="Cleanup old jobs",
    description="Remove old completed jobs from the database"
)
async def cleanup_old_jobs(
    older_than_days: int = 30,
    keep_failed: bool = True,
    db: AsyncSession = Depends(get_db),
    api_key: ApiKey | None = Depends(get_optional_api_key),
) -> dict:
    """
    Clean up old jobs from the database.

    Args:
        older_than_days: Remove jobs older than this many days
        keep_failed: Whether to keep failed jobs for debugging
    """
    try:
        deleted_count = await job_crud.delete_old_jobs(
            db,
            older_than_days=older_than_days,
            keep_failed=keep_failed
        )

        logger.info(f"Cleaned up {deleted_count} old jobs (older than {older_than_days} days)")

        return {
            "deleted_count": deleted_count,
            "older_than_days": older_than_days,
            "kept_failed": keep_failed,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup old jobs"
        )


@router.get(
    "/admin/metrics",
    summary="Get Prometheus-style metrics",
    description="Get metrics in Prometheus format for monitoring"
)
async def get_metrics(
    db: AsyncSession = Depends(get_db),
    api_key: ApiKey | None = Depends(get_optional_api_key),
) -> str:
    """
    Get metrics in Prometheus format.

    This endpoint returns metrics that can be scraped by Prometheus
    or other monitoring systems.
    """
    try:
        # Get job statistics
        api_key_id = api_key.id if api_key else None
        stats = await job_crud.get_job_stats(db, api_key_id=api_key_id)

        # Get queue statistics
        redis_client = await get_redis()
        queue = RedisQueue(redis_client)
        queue_stats = await queue.get_queue_stats()

        # Generate Prometheus-style metrics
        metrics = []

        # Job metrics
        metrics.append(f"scraper_jobs_total {stats['total']}")
        metrics.append(f"scraper_jobs_pending {stats['pending']}")
        metrics.append(f"scraper_jobs_running {stats['running']}")
        metrics.append(f"scraper_jobs_completed {stats['completed']}")
        metrics.append(f"scraper_jobs_failed {stats['failed']}")
        metrics.append(f"scraper_jobs_cancelled {stats['cancelled']}")
        metrics.append(f"scraper_jobs_retrying {stats['retrying']}")
        metrics.append(f"scraper_jobs_avg_execution_time {stats['average_execution_time']}")

        # Queue metrics
        metrics.append(f"scraper_queue_pending {queue_stats['pending']}")
        metrics.append(f"scraper_queue_processing {queue_stats['processing']}")
        metrics.append(f"scraper_queue_total {queue_stats['total']}")

        # System metrics (if available)
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()

            metrics.append(f"scraper_system_cpu_percent {cpu_percent}")
            metrics.append(f"scraper_system_memory_percent {memory.percent}")
            metrics.append(f"scraper_system_memory_used {memory.used}")
            metrics.append(f"scraper_system_memory_available {memory.available}")
        except Exception:
            pass  # Skip system metrics if not available

        return "\n".join(metrics)

    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate metrics"
        )


@router.get(
    "/admin/queue",
    response_model=QueueStatsResponse,
    summary="Get queue status",
    description="Get detailed queue statistics"
)
async def get_queue_status() -> QueueStatsResponse:
    """
    Get detailed queue statistics.
    """
    try:
        redis_client = await get_redis()
        queue = RedisQueue(redis_client)
        stats = await queue.get_queue_stats()

        return QueueStatsResponse(
            pending=stats["pending"],
            processing=stats["processing"],
            total=stats["total"],
            workers=1,  # This would be dynamic in a real implementation
        )

    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve queue statistics"
        )

"""
Job queue management service using Redis.

This module provides job queue functionality for the web scraping API,
including job enqueuing, dequeuing, priority handling, and retry logic.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from app.core.cache import get_redis_client, set_job_status
from app.core.config import get_settings
from app.core.database import get_db_session
from app.models import Job, JobStatus

logger = logging.getLogger(__name__)


class JobQueue:
    """Job queue manager using Redis."""

    def __init__(self):
        self.settings = get_settings()
        self.redis = get_redis_client()
        self.queue_key = "job_queue"
        self.processing_key = "processing_jobs"
        self.retry_key = "retry_queue"
        self.dlq_key = "dead_letter_queue"  # Dead letter queue for failed jobs

    async def enqueue_job(
        self,
        job_id: str,
        priority: int = 0,
        delay_seconds: int = 0
    ) -> bool:
        """
        Add job to processing queue.

        Args:
            job_id: UUID of the job to enqueue
            priority: Job priority (lower number = higher priority)
            delay_seconds: Delay before job becomes available for processing

        Returns:
            True if job was enqueued successfully, False otherwise
        """
        try:
            # Calculate the score (timestamp + priority)
            # Jobs with lower priority numbers and earlier timestamps are processed first
            base_time = datetime.utcnow().timestamp()
            delayed_time = base_time + delay_seconds
            score = delayed_time + (priority * 1000)  # Priority affects ordering significantly

            # Add to sorted set (priority queue)
            result = await self.redis.zadd(self.queue_key, {job_id: score})

            if result:
                # Update job status in Redis
                await set_job_status(job_id, "queued", {
                    "queued_at": datetime.utcnow().isoformat(),
                    "priority": priority,
                    "estimated_start": (datetime.utcnow() + timedelta(seconds=delay_seconds)).isoformat()
                })

                logger.info(f"Job {job_id} enqueued with priority {priority}, delay {delay_seconds}s")
                return True
            else:
                logger.warning(f"Job {job_id} was already in queue")
                return False

        except Exception as e:
            logger.error(f"Failed to enqueue job {job_id}: {e}")
            return False

    async def dequeue_job(self, timeout: int = 5) -> str | None:
        """
        Get next job from queue (blocking operation).

        Args:
            timeout: Maximum time to wait for a job in seconds

        Returns:
            Job ID string if available, None if timeout or error
        """
        try:
            current_time = datetime.utcnow().timestamp()

            # Get jobs that are ready to be processed (score <= current_time)
            jobs = await self.redis.zrangebyscore(
                self.queue_key,
                min=0,
                max=current_time,
                start=0,
                num=1,
                withscores=False
            )

            if not jobs:
                # No jobs ready, wait a bit and try again
                await asyncio.sleep(min(timeout, 1))
                return None

            job_id = jobs[0]

            # Atomically move job from queue to processing
            pipe = self.redis.pipeline()
            pipe.zrem(self.queue_key, job_id)
            pipe.sadd(self.processing_key, job_id)
            pipe.setex(f"processing:{job_id}", 3600, datetime.utcnow().isoformat())
            results = await pipe.execute()

            if results[0]:  # Successfully removed from queue
                # Update job status
                await set_job_status(job_id, "processing", {
                    "started_at": datetime.utcnow().isoformat(),
                    "worker_id": f"worker-{id(self)}"
                })

                logger.info(f"Job {job_id} dequeued for processing")
                return job_id
            else:
                logger.warning(f"Job {job_id} was not in queue (may have been processed by another worker)")
                return None

        except Exception as e:
            logger.error(f"Failed to dequeue job: {e}")
            return None

    async def complete_job(self, job_id: str, success: bool = True, result_data: dict | None = None, error_message: str | None = None) -> bool:
        """
        Mark job as completed and remove from processing set.

        Args:
            job_id: Job ID to complete
            success: Whether job completed successfully
            result_data: Job result data (if successful)
            error_message: Error message (if failed)

        Returns:
            True if job was marked complete successfully
        """
        try:
            # Remove from processing set
            await self.redis.srem(self.processing_key, job_id)
            await self.redis.delete(f"processing:{job_id}")

            if success:
                # Update job status to completed
                await set_job_status(job_id, "completed", {
                    "completed_at": datetime.utcnow().isoformat(),
                    "result": result_data or {}
                })
                logger.info(f"Job {job_id} marked as completed successfully")
            else:
                # Update job status to failed
                await set_job_status(job_id, "failed", {
                    "failed_at": datetime.utcnow().isoformat(),
                    "error": error_message or "Unknown error"
                })

                # Check if job should be retried
                should_retry = await self._should_retry_job(job_id)
                if should_retry:
                    await self._schedule_retry(job_id)
                else:
                    # Move to dead letter queue
                    await self.redis.lpush(self.dlq_key, job_id)

                logger.warning(f"Job {job_id} marked as failed: {error_message}")

            return True

        except Exception as e:
            logger.error(f"Failed to complete job {job_id}: {e}")
            return False

    async def _should_retry_job(self, job_id: str) -> bool:
        """Check if job should be retried based on retry count and settings."""
        try:
            async with get_db_session() as session:
                job = await session.get(Job, UUID(job_id))
                return bool(job and job.retry_count < job.max_retries)
        except Exception as e:
            logger.error(f"Failed to check retry status for job {job_id}: {e}")
            return False

    async def _schedule_retry(self, job_id: str) -> None:
        """Schedule job for retry with exponential backoff."""
        try:
            async with get_db_session() as session:
                job = await session.get(Job, UUID(job_id))
                if not job:
                    return

                # Update retry count
                job.retry_count += 1
                job.status = JobStatus.RETRYING
                await session.commit()

                # Calculate retry delay (exponential backoff)
                base_delay = self.settings.RETRY_DELAY
                delay_seconds = base_delay * (self.settings.RETRY_BACKOFF ** (job.retry_count - 1))
                max_delay = 300  # Max 5 minutes
                delay_seconds = min(delay_seconds, max_delay)

                # Add to retry queue with delay
                retry_time = datetime.utcnow().timestamp() + delay_seconds
                await self.redis.zadd(self.retry_key, {job_id: retry_time})

                await set_job_status(job_id, "retrying", {
                    "retry_count": job.retry_count,
                    "retry_at": (datetime.utcnow() + timedelta(seconds=delay_seconds)).isoformat(),
                    "delay_seconds": delay_seconds
                })

                logger.info(f"Job {job_id} scheduled for retry #{job.retry_count} in {delay_seconds}s")

        except Exception as e:
            logger.error(f"Failed to schedule retry for job {job_id}: {e}")

    async def process_retry_queue(self) -> int:
        """Process retry queue and move ready jobs back to main queue."""
        try:
            current_time = datetime.utcnow().timestamp()

            # Get jobs ready for retry
            retry_jobs = await self.redis.zrangebyscore(
                self.retry_key,
                min=0,
                max=current_time,
                withscores=False
            )

            if not retry_jobs:
                return 0

            moved_count = 0
            for job_id in retry_jobs:
                # Move from retry queue to main queue
                pipe = self.redis.pipeline()
                pipe.zrem(self.retry_key, job_id)
                pipe.zadd(self.queue_key, {job_id: current_time})  # Add with current timestamp
                results = await pipe.execute()

                if results[0]:  # Successfully moved
                    await set_job_status(job_id, "queued", {
                        "requeued_at": datetime.utcnow().isoformat(),
                        "retry_attempt": True
                    })
                    moved_count += 1
                    logger.info(f"Job {job_id} moved from retry queue to main queue")

            if moved_count > 0:
                logger.info(f"Moved {moved_count} jobs from retry queue to main queue")

            return moved_count

        except Exception as e:
            logger.error(f"Failed to process retry queue: {e}")
            return 0

    async def get_queue_stats(self) -> dict[str, Any]:
        """Get queue statistics."""
        try:
            stats = {
                "queue_size": await self.redis.zcard(self.queue_key),
                "processing_count": await self.redis.scard(self.processing_key),
                "retry_queue_size": await self.redis.zcard(self.retry_key),
                "dead_letter_queue_size": await self.redis.llen(self.dlq_key),
                "timestamp": datetime.utcnow().isoformat()
            }

            # Get next job info
            next_jobs = await self.redis.zrange(self.queue_key, 0, 0, withscores=True)
            if next_jobs:
                job_id, score = next_jobs[0]
                next_run_time = datetime.fromtimestamp(score)
                stats["next_job"] = {
                    "job_id": job_id,
                    "scheduled_time": next_run_time.isoformat(),
                    "seconds_until_ready": max(0, (next_run_time - datetime.utcnow()).total_seconds())
                }

            return stats

        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    async def cleanup_stale_jobs(self, max_processing_time: int = 3600) -> int:
        """Clean up jobs that have been processing for too long."""
        try:
            current_time = datetime.utcnow()
            cleanup_count = 0

            # Get all processing jobs
            processing_jobs = await self.redis.smembers(self.processing_key)

            for job_id in processing_jobs:
                processing_start = await self.redis.get(f"processing:{job_id}")
                if not processing_start:
                    # No processing timestamp, clean up
                    await self.redis.srem(self.processing_key, job_id)
                    await self._schedule_retry(job_id)  # Retry the job
                    cleanup_count += 1
                    continue

                # Check if processing time exceeded
                start_time = datetime.fromisoformat(processing_start)
                if (current_time - start_time).total_seconds() > max_processing_time:
                    # Job has been processing too long, clean up and retry
                    await self.redis.srem(self.processing_key, job_id)
                    await self.redis.delete(f"processing:{job_id}")
                    await self._schedule_retry(job_id)
                    cleanup_count += 1
                    logger.warning(f"Cleaned up stale job {job_id} (processing for {(current_time - start_time).total_seconds()}s)")

            if cleanup_count > 0:
                logger.info(f"Cleaned up {cleanup_count} stale jobs")

            return cleanup_count

        except Exception as e:
            logger.error(f"Failed to cleanup stale jobs: {e}")
            return 0


# Global queue instance
_job_queue: JobQueue | None = None

def get_job_queue() -> JobQueue:
    """Get global job queue instance."""
    global _job_queue
    if _job_queue is None:
        _job_queue = JobQueue()
    return _job_queue


# Convenience functions for common operations
async def enqueue_job(job_id: str, priority: int = 0, delay_seconds: int = 0) -> bool:
    """Enqueue a job for processing."""
    queue = get_job_queue()
    return await queue.enqueue_job(job_id, priority, delay_seconds)


async def dequeue_job(timeout: int = 5) -> str | None:
    """Dequeue next job for processing."""
    queue = get_job_queue()
    return await queue.dequeue_job(timeout)


async def complete_job(job_id: str, success: bool = True, result_data: dict | None = None, error_message: str | None = None) -> bool:
    """Mark job as completed."""
    queue = get_job_queue()
    return await queue.complete_job(job_id, success, result_data, error_message)

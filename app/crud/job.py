"""CRUD operations for Job model."""
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, desc, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from app.models.job import Job, JobStatus


class JobCRUD:
    """CRUD operations for Job model."""

    async def create(
        self,
        db: AsyncSession,
        *,
        url: str,
        selector: str | None = None,
        options: dict[str, Any] | None = None,
        priority: int = 0,
        scheduled_at: datetime | None = None,
        api_key_id: UUID | None = None,
        max_retries: int = 3,
        metadata: dict[str, Any] | None = None,
    ) -> Job:
        """Create a new job."""
        job = Job(
            url=url,
            selector=selector,
            options=options or {},
            priority=priority,
            scheduled_at=scheduled_at,
            api_key_id=api_key_id,
            max_retries=max_retries,
            metadata=metadata or {},
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job

    async def get(self, db: AsyncSession, job_id: UUID) -> Job | None:
        """Get job by ID."""
        result = await db.execute(
            select(Job).where(Job.id == job_id).options(joinedload(Job.result))
        )
        return result.scalar_one_or_none()

    async def get_by_status(
        self,
        db: AsyncSession,
        status: JobStatus,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Job]:
        """Get jobs by status."""
        result = await db.execute(
            select(Job)
            .where(Job.status == status)
            .order_by(desc(Job.priority), Job.created_at)
            .limit(limit)
            .offset(offset)
            .options(joinedload(Job.result))
        )
        return result.scalars().all()

    async def get_pending_jobs(
        self,
        db: AsyncSession,
        limit: int = 100,
    ) -> list[Job]:
        """Get pending jobs ordered by priority and creation time."""
        now = datetime.utcnow()
        result = await db.execute(
            select(Job)
            .where(
                and_(
                    Job.status == JobStatus.PENDING,
                    or_(Job.scheduled_at.is_(None), Job.scheduled_at <= now)
                )
            )
            .order_by(desc(Job.priority), Job.created_at)
            .limit(limit)
            .options(joinedload(Job.result))
        )
        return result.scalars().all()

    async def get_failed_retryable_jobs(
        self,
        db: AsyncSession,
        limit: int = 100,
    ) -> list[Job]:
        """Get failed jobs that can be retried."""
        result = await db.execute(
            select(Job)
            .where(
                and_(
                    Job.status == JobStatus.FAILED,
                    Job.retry_count < Job.max_retries
                )
            )
            .order_by(desc(Job.priority), Job.created_at)
            .limit(limit)
            .options(joinedload(Job.result))
        )
        return result.scalars().all()

    async def update_status(
        self,
        db: AsyncSession,
        job_id: UUID,
        status: JobStatus,
        error_message: str | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> Job | None:
        """Update job status."""
        job = await self.get(db, job_id)
        if not job:
            return None

        job.status = status
        if error_message is not None:
            job.error_message = error_message
        if started_at is not None:
            job.started_at = started_at
        if completed_at is not None:
            job.completed_at = completed_at

        await db.commit()
        await db.refresh(job)
        return job

    async def increment_retry_count(
        self,
        db: AsyncSession,
        job_id: UUID,
    ) -> Job | None:
        """Increment retry count and set status to pending."""
        job = await self.get(db, job_id)
        if not job:
            return None

        job.retry_count += 1
        job.status = JobStatus.PENDING
        job.error_message = None
        job.started_at = None
        job.completed_at = None

        await db.commit()
        await db.refresh(job)
        return job

    async def get_recent_jobs(
        self,
        db: AsyncSession,
        limit: int = 50,
        api_key_id: UUID | None = None,
    ) -> list[Job]:
        """Get recent jobs."""
        query = select(Job).order_by(desc(Job.created_at)).limit(limit)

        if api_key_id:
            query = query.where(Job.api_key_id == api_key_id)

        result = await db.execute(query.options(joinedload(Job.result)))
        return result.scalars().all()

    async def get_job_stats(
        self,
        db: AsyncSession,
        api_key_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Get job statistics."""
        base_query = select(func.count(Job.id))

        if api_key_id:
            base_query = base_query.where(Job.api_key_id == api_key_id)

        # Total jobs
        total_result = await db.execute(base_query)
        total = total_result.scalar()

        # Jobs by status
        stats = {"total": total}

        for status in JobStatus:
            status_query = base_query.where(Job.status == status)
            result = await db.execute(status_query)
            stats[status.value] = result.scalar()

        # Average execution time for completed jobs
        execution_time_query = select(
            func.avg(
                func.extract("epoch", Job.completed_at - Job.started_at)
            )
        ).where(
            and_(
                Job.status == JobStatus.COMPLETED,
                Job.started_at.is_not(None),
                Job.completed_at.is_not(None)
            )
        )

        if api_key_id:
            execution_time_query = execution_time_query.where(Job.api_key_id == api_key_id)

        result = await db.execute(execution_time_query)
        avg_execution_time = result.scalar()
        stats["average_execution_time"] = float(avg_execution_time) if avg_execution_time else 0

        return stats

    async def delete_old_jobs(
        self,
        db: AsyncSession,
        older_than_days: int = 30,
        keep_failed: bool = True,
    ) -> int:
        """Delete old jobs."""
        cutoff_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_date = cutoff_date.replace(day=cutoff_date.day - older_than_days)

        query = select(Job).where(Job.created_at < cutoff_date)

        if keep_failed:
            query = query.where(Job.status != JobStatus.FAILED)

        result = await db.execute(query)
        jobs_to_delete = result.scalars().all()

        for job in jobs_to_delete:
            await db.delete(job)

        await db.commit()
        return len(jobs_to_delete)


# Create a global instance
job_crud = JobCRUD()

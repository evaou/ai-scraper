"""Scraping API route handlers."""
import logging
import math
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    CommonQueryParams,
    check_rate_limit,
    get_api_key_when_required,
    get_optional_api_key,
)
from app.core.database import get_db
from app.core.redis import RedisQueue, get_redis
from app.crud.job import job_crud
from app.models.api_key import ApiKey
from app.models.job import JobStatus
from app.schemas.scraping import (
    JobDetailResponse,
    JobListResponse,
    JobStatsResponse,
    ScrapeRequest,
    ScrapeResponse,
)
from app.services.scraper import create_scraping_metadata, create_scraping_result

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/scrape",
    response_model=ScrapeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit scraping job",
    description="Submit a new web scraping job to the queue. Requires API key when API_KEY_REQUIRED=true."
)
async def submit_scrape_job(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    api_key: ApiKey | None = Depends(get_api_key_when_required),
    _rate_limit: None = Depends(check_rate_limit),
) -> ScrapeResponse:
    """
    Submit a new scraping job.

    The job will be queued for processing by workers and returns immediately
    with a job ID that can be used to check status and retrieve results.
    """
    try:
        # Create job in database
        job = await job_crud.create(
            db,
            url=str(request.url),
            selector=request.selector,
            options=request.options.dict() if request.options else {},
            priority=request.priority,
            scheduled_at=request.scheduled_at,
            api_key_id=api_key.id if api_key else None,
            metadata=request.metadata or {},
        )

        # Add job to Redis queue
        redis_client = await get_redis()
        queue = RedisQueue(redis_client)

        success = await queue.enqueue(str(job.id), priority=request.priority)
        if not success:
            logger.error(f"Failed to enqueue job {job.id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to queue job for processing"
            )

        # Estimate completion time (rough calculation)
        estimated_completion = None
        if request.scheduled_at:
            estimated_completion = request.scheduled_at
        else:
            # Simple estimation: current time + average processing time
            # This would be more sophisticated in production
            estimated_completion = datetime.utcnow() + timedelta(seconds=30)

        logger.info(f"Job {job.id} created and queued successfully")

        return ScrapeResponse(
            job_id=job.id,
            status=job.status.value,
            url=job.url,
            created_at=job.created_at,
            estimated_completion=estimated_completion,
            priority=job.priority,
        )

    except Exception as e:
        logger.error(f"Error creating scrape job: {e}")
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create scraping job"
        )


@router.get(
    "/scrape/{job_id}",
    response_model=JobDetailResponse,
    summary="Get job details",
    description="Get detailed information about a scraping job including results if completed"
)
async def get_job_details(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    api_key: ApiKey | None = Depends(get_optional_api_key),
) -> JobDetailResponse:
    """
    Get detailed job information including results if available.
    """
    try:
        job = await job_crud.get(db, job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )

        # Check if user has access to this job
        if api_key and job.api_key_id != api_key.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this job"
            )

        # Convert result data to structured format
        scraped_data = None
        metadata = None

        if job.result and job.status == JobStatus.COMPLETED:
            # Create structured result from database result
            scraped_data = create_scraping_result(job.result.data)
            metadata = create_scraping_metadata(job.result.result_metadata or {}, job)

        return JobDetailResponse(
            job_id=job.id,
            status=job.status.value,
            url=job.url,
            selector=job.selector,
            options=job.options,
            priority=job.priority,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            retry_count=job.retry_count,
            max_retries=job.max_retries,
            error_message=job.error_message,
            data=scraped_data,
            metadata=metadata,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job details for {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job details"
        )


@router.get(
    "/results",
    response_model=JobListResponse,
    summary="List recent jobs",
    description="Get a paginated list of recent scraping jobs"
)
async def list_recent_jobs(
    params: CommonQueryParams = Depends(),
    db: AsyncSession = Depends(get_db),
    api_key: ApiKey | None = Depends(get_optional_api_key),
    status_filter: str | None = None,
) -> JobListResponse:
    """
    Get a paginated list of recent jobs.
    """
    try:
        # Get jobs based on API key (if authenticated)
        api_key_id = api_key.id if api_key else None

        if status_filter:
            # Validate status filter
            try:
                status_enum = JobStatus(status_filter.lower())
                jobs = await job_crud.get_by_status(
                    db,
                    status=status_enum,
                    limit=params.limit,
                    offset=params.offset
                )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status filter: {status_filter}"
                )
        else:
            jobs = await job_crud.get_recent_jobs(
                db,
                limit=params.limit,
                api_key_id=api_key_id
            )

        # Convert to response format
        job_responses = []
        for job in jobs:
            scraped_data = None
            metadata = None

            if job.result and job.status == JobStatus.COMPLETED:
                scraped_data = create_scraping_result(job.result.data)
                metadata = create_scraping_metadata(job.result.result_metadata or {}, job)

            job_responses.append(JobDetailResponse(
                job_id=job.id,
                status=job.status.value,
                url=job.url,
                selector=job.selector,
                options=job.options,
                priority=job.priority,
                created_at=job.created_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
                retry_count=job.retry_count,
                max_retries=job.max_retries,
                error_message=job.error_message,
                data=scraped_data,
                metadata=metadata,
            ))

        # Get total count for pagination
        # In a real implementation, you'd want a separate count query
        total = len(job_responses)  # Simplified
        pages = math.ceil(total / params.per_page) if params.per_page > 0 else 1

        return JobListResponse(
            jobs=job_responses,
            total=total,
            page=params.page,
            per_page=params.per_page,
            pages=pages,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve jobs"
        )


@router.get(
    "/stats",
    response_model=JobStatsResponse,
    summary="Get job statistics",
    description="Get statistics about scraping jobs"
)
async def get_job_stats(
    db: AsyncSession = Depends(get_db),
    api_key: ApiKey | None = Depends(get_optional_api_key),
) -> JobStatsResponse:
    """
    Get job statistics.
    """
    try:
        api_key_id = api_key.id if api_key else None
        stats = await job_crud.get_job_stats(db, api_key_id=api_key_id)

        return JobStatsResponse(
            total=stats["total"],
            pending=stats["pending"],
            running=stats["running"],
            completed=stats["completed"],
            failed=stats["failed"],
            cancelled=stats["cancelled"],
            retrying=stats["retrying"],
            average_execution_time=stats["average_execution_time"],
        )

    except Exception as e:
        logger.error(f"Error getting job stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job statistics"
        )


@router.delete(
    "/scrape/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel job",
    description="Cancel a pending or running scraping job"
)
async def cancel_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    api_key: ApiKey | None = Depends(get_optional_api_key),
) -> None:
    """
    Cancel a scraping job.

    Only pending or running jobs can be cancelled.
    """
    try:
        job = await job_crud.get(db, job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )

        # Check access permissions
        if api_key and job.api_key_id != api_key.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this job"
            )

        # Check if job can be cancelled
        if job.status not in [JobStatus.PENDING, JobStatus.RUNNING]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel job with status: {job.status.value}"
            )

        # Update job status to cancelled
        await job_crud.update_status(
            db,
            job_id,
            JobStatus.CANCELLED,
            error_message="Job cancelled by user"
        )

        # Note: Queue cleanup would be handled by worker polling

        logger.info(f"Job {job_id} cancelled successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel job"
        )

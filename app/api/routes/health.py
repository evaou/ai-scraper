"""Health check API routes."""
import asyncio
import logging
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.schemas.scraping import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# Track application start time for uptime calculation
start_time = time.time()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check the health status of the API and its dependencies"
)
async def health_check(
    db: AsyncSession = Depends(get_db)
) -> HealthResponse:
    """
    Perform health checks on the API and its dependencies.

    Returns the overall health status and individual component checks.
    """
    checks = {}
    overall_status = "healthy"

    # Check database connection
    try:
        await asyncio.wait_for(
            db.execute(text("SELECT 1")),
            timeout=settings.HEALTH_CHECK_TIMEOUT
        )
        checks["database"] = True
        logger.debug("Database health check passed")
    except Exception as e:
        checks["database"] = False
        overall_status = "unhealthy"
        logger.error(f"Database health check failed: {e}")

    # Check Redis connection
    try:
        redis_client = await get_redis()
        await asyncio.wait_for(
            redis_client.ping(),
            timeout=settings.HEALTH_CHECK_TIMEOUT
        )
        checks["redis"] = True
        logger.debug("Redis health check passed")
    except Exception as e:
        checks["redis"] = False
        overall_status = "unhealthy"
        logger.error(f"Redis health check failed: {e}")

    # Calculate uptime
    uptime = time.time() - start_time

    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        version=settings.PROJECT_VERSION,
        uptime=uptime,
        checks=checks
    )


@router.get(
    "/health/ready",
    summary="Readiness check",
    description="Check if the service is ready to handle requests"
)
async def readiness_check(
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Kubernetes-style readiness probe.

    Returns 200 if the service is ready to handle requests,
    503 if not ready.
    """
    try:
        # Quick database check
        await asyncio.wait_for(
            db.execute(text("SELECT 1")),
            timeout=2  # Shorter timeout for readiness
        )

        # Quick Redis check
        redis_client = await get_redis()
        await asyncio.wait_for(
            redis_client.ping(),
            timeout=2
        )

        return {"status": "ready"}

    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )


@router.get(
    "/health/live",
    summary="Liveness check",
    description="Check if the service is alive"
)
async def liveness_check() -> dict:
    """
    Kubernetes-style liveness probe.

    Returns 200 if the service is alive.
    """
    return {"status": "alive"}


@router.get(
    "/version",
    summary="Get API version",
    description="Get the current API version information"
)
async def get_version() -> dict:
    """
    Get API version and build information.
    """
    return {
        "version": settings.PROJECT_VERSION,
        "name": settings.PROJECT_NAME,
        "api_version": settings.API_V1_STR,
        "uptime": time.time() - start_time
    }


@router.get(
    "/metrics",
    summary="Get application metrics",
    description="Get basic application metrics for monitoring"
)
async def get_metrics(
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get application metrics for monitoring purposes.
    
    This endpoint is used by the deployment health checks and monitoring systems.
    """
    try:
        # Basic metrics
        uptime = time.time() - start_time
        
        # Check service health
        db_healthy = True
        redis_healthy = True
        
        try:
            await asyncio.wait_for(
                db.execute(text("SELECT 1")),
                timeout=2
            )
        except Exception:
            db_healthy = False
        
        try:
            redis_client = await get_redis()
            await asyncio.wait_for(
                redis_client.ping(),
                timeout=2
            )
        except Exception:
            redis_healthy = False
        
        return {
            "status": "healthy" if (db_healthy and redis_healthy) else "unhealthy",
            "uptime_seconds": uptime,
            "version": settings.PROJECT_VERSION,
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "database": "healthy" if db_healthy else "unhealthy",
                "redis": "healthy" if redis_healthy else "unhealthy"
            },
            "metrics": {
                "requests_total": "not_implemented",
                "active_connections": "not_implemented"
            }
        }
    except Exception as e:
        logger.error(f"Metrics endpoint error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

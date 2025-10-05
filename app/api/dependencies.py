"""FastAPI dependencies for authentication and rate limiting."""
import logging

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.cache import rate_limit_check
from app.core.config import get_settings
from app.core.database import get_db
from app.models import ApiKey

logger = logging.getLogger(__name__)

# Security scheme for API keys
security = HTTPBearer(auto_error=False)


async def get_current_api_key(
    request: Request,
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(security)
) -> ApiKey | None:
    """
    Get and validate API key from request headers.

    Returns None if API keys are not required or if no key is provided.
    Raises HTTPException for invalid keys.
    """
    settings = get_settings()
    if not settings.API_KEY_REQUIRED:
        return None

    # Try to get API key from Authorization header first
    api_key = None
    if credentials:
        api_key = credentials.credentials
    else:
        # Try custom header
        api_key = request.headers.get(settings.API_KEY_HEADER)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Hash the provided key to compare with stored hash
    key_hash = ApiKey.hash_key(api_key)

    # Query database for API key
    result = await db.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash)
    )
    api_key_obj = result.scalar_one_or_none()

    if not api_key_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    if not api_key_obj.is_valid:
        detail = "API key expired" if api_key_obj.is_expired else "API key inactive"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )

    # Update usage statistics
    api_key_obj.update_last_used()
    await db.commit()

    return api_key_obj


async def check_rate_limit(
    request: Request,
    api_key: ApiKey | None = Depends(get_current_api_key)
) -> None:
    """
    Check rate limits for the current request.

    Raises HTTPException if rate limit is exceeded.
    """
    settings = get_settings()

    try:
        # Determine rate limits and identifier
        if api_key:
            # Use API key specific limits
            minute_limit = api_key.rate_limit_per_minute
            hour_limit = api_key.rate_limit_per_hour
            key_identifier = f"api_key:{api_key.id}"
        else:
            # Use global/IP-based limits
            minute_limit = settings.RATE_LIMIT_PER_MINUTE
            hour_limit = settings.RATE_LIMIT_PER_HOUR
            client_ip = request.client.host if request.client else "unknown"
            key_identifier = f"ip:{client_ip}"

        # Check per-minute rate limit
        minute_result = await rate_limit_check(
            f"{key_identifier}:minute",
            minute_limit,
            60  # 1 minute window
        )

        if not minute_result.get("allowed", True):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded - too many requests per minute",
                headers={
                    "X-RateLimit-Limit": str(minute_limit),
                    "X-RateLimit-Remaining": str(max(0, minute_limit - minute_result.get("current_count", 0))),
                    "X-RateLimit-Reset": minute_result.get("reset_time", ""),
                    "Retry-After": "60"
                }
            )

        # Check per-hour rate limit
        hour_result = await rate_limit_check(
            f"{key_identifier}:hour",
            hour_limit,
            3600  # 1 hour window
        )

        if not hour_result.get("allowed", True):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded - too many requests per hour",
                headers={
                    "X-RateLimit-Limit": str(hour_limit),
                    "X-RateLimit-Remaining": str(max(0, hour_limit - hour_result.get("current_count", 0))),
                    "X-RateLimit-Reset": hour_result.get("reset_time", ""),
                    "Retry-After": "3600"
                }
            )

        logger.debug(
            f"Rate limit check passed for {key_identifier}: "
            f"{minute_result.get('current_count', 0)}/{minute_limit} per minute, "
            f"{hour_result.get('current_count', 0)}/{hour_limit} per hour"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking rate limit: {e}")
        # Allow request to proceed in case of rate limit check failure


async def get_optional_api_key(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> ApiKey | None:
    """
    Get API key if provided, but don't require it.
    Used for endpoints that work both with and without authentication.
    """
    settings = get_settings()
    if not settings.API_KEY_REQUIRED:
        # Still try to get the key if provided for tracking purposes
        api_key = request.headers.get(settings.API_KEY_HEADER)
        if api_key:
            key_hash = ApiKey.hash_key(api_key)
            result = await db.execute(
                select(ApiKey).where(ApiKey.key_hash == key_hash)
            )
            api_key_obj = result.scalar_one_or_none()
            if api_key_obj and api_key_obj.is_valid:
                api_key_obj.update_last_used()
                await db.commit()
                return api_key_obj

    return None


def get_client_ip(request: Request) -> str:
    """
    Get client IP address from request.

    Handles X-Forwarded-For, X-Real-IP headers for reverse proxy setups.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Get first IP if multiple are present
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fallback to direct client IP
    return request.client.host if request.client else "unknown"


class CommonQueryParams:
    """
    Common query parameters for pagination.
    """
    def __init__(
        self,
        page: int = 1,
        per_page: int = 20,
        sort: str = "created_at",
        order: str = "desc"
    ):
        self.page = max(1, page)
        self.per_page = min(100, max(1, per_page))  # Limit to 100 items per page
        self.sort = sort
        self.order = order.lower() if order.lower() in ["asc", "desc"] else "desc"

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page

    @property
    def limit(self) -> int:
        return self.per_page

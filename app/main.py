"""Main FastAPI application."""
import logging
import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import admin, health, scraping
from app.core.config import settings
from app.core.database import close_db, init_db
from app.core.redis import close_redis, init_redis
from app.schemas.scraping import ErrorResponse

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer() if settings.LOG_FORMAT == "json" else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        logging.getLevelName(settings.LOG_LEVEL.upper())
    ),
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan events for startup and shutdown tasks.
    """
    # Startup
    logger.info("Starting up Web Scraping API", version=settings.PROJECT_VERSION)

    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized successfully")

        # Initialize Redis
        await init_redis()
        logger.info("Redis initialized successfully")

        logger.info("Application startup completed successfully")

    except Exception as e:
        logger.error("Failed to initialize application", error=str(e))
        raise

    yield

    # Shutdown
    logger.info("Shutting down Web Scraping API")

    try:
        # Close database connections
        await close_db()
        logger.info("Database connections closed")

        # Close Redis connections
        await close_redis()
        logger.info("Redis connections closed")

        logger.info("Application shutdown completed successfully")

    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="A production-ready, scalable web scraping API built with FastAPI, Playwright, and containerized architecture.",
    version=settings.PROJECT_VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.DEBUG else None,
    docs_url=f"{settings.API_V1_STR}/docs" if settings.DEBUG else None,
    redoc_url=f"{settings.API_V1_STR}/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
    # Custom OpenAPI configuration
    openapi_tags=[
        {
            "name": "scraping",
            "description": "Web scraping operations - submit jobs, check status, and retrieve results",
        },
        {
            "name": "health",
            "description": "Health checks and system status monitoring",
        },
        {
            "name": "admin",
            "description": "Administrative operations and system metrics",
        },
    ]
)

# Add CORS middleware
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Add trusted host middleware for production security
if not settings.DEBUG:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log all incoming requests with timing information.
    """
    start_time = time.time()

    # Get client IP (accounting for proxies)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"

    # Process request
    response = await call_next(request)

    # Calculate processing time
    process_time = time.time() - start_time

    # Log request
    logger.info(
        "HTTP request processed",
        method=request.method,
        url=str(request.url),
        client_ip=client_ip,
        status_code=response.status_code,
        process_time=round(process_time, 3),
        user_agent=request.headers.get("user-agent", ""),
    )

    # Add timing header
    response.headers["X-Process-Time"] = str(process_time)

    return response


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle HTTP exceptions with consistent error format.
    """
    from fastapi.encoders import jsonable_encoder

    logger.warning(
        "HTTP exception occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        url=str(request.url),
        method=request.method,
    )

    error_response = ErrorResponse(
        error="HTTPException",
        message=exc.detail,
        details={"status_code": exc.status_code}
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(error_response),
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle request validation errors with detailed information.
    """
    from fastapi.encoders import jsonable_encoder

    logger.warning(
        "Request validation error",
        errors=exc.errors(),
        url=str(request.url),
        method=request.method,
    )

    error_response = ErrorResponse(
        error="ValidationError",
        message="Request validation failed",
        details={
            "errors": exc.errors(),
            "body": exc.body if hasattr(exc, "body") else None,
        }
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(error_response),
    )


@app.exception_handler(StarletteHTTPException)
async def starlette_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handle Starlette HTTP exceptions.
    """
    from fastapi.encoders import jsonable_encoder

    logger.error(
        "Starlette HTTP exception",
        status_code=exc.status_code,
        detail=exc.detail,
        url=str(request.url),
        method=request.method,
    )

    error_response = ErrorResponse(
        error="StarletteHTTPException",
        message=exc.detail,
        details={"status_code": exc.status_code}
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(error_response),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions.
    """
    from fastapi.encoders import jsonable_encoder

    logger.error(
        "Unexpected exception occurred",
        error=str(exc),
        type=type(exc).__name__,
        url=str(request.url),
        method=request.method,
        exc_info=True,
    )

    error_response = ErrorResponse(
        error="InternalServerError",
        message="An unexpected error occurred" if not settings.DEBUG else str(exc),
        details={"type": type(exc).__name__} if settings.DEBUG else None
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=jsonable_encoder(error_response),
    )


# Include routers
app.include_router(
    scraping.router,
    prefix=f"{settings.API_V1_STR}/scraping",
    tags=["scraping"],
)

app.include_router(
    health.router,
    prefix=settings.API_V1_STR,
    tags=["health"],
)

app.include_router(
    admin.router,
    prefix=settings.API_V1_STR,
    tags=["admin"],
)


# Root endpoint
@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    """
    Root endpoint providing basic API information.
    """
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "status": "running",
        "docs_url": f"{settings.API_V1_STR}/docs" if settings.DEBUG else "disabled",
        "api_version": settings.API_V1_STR,
    }


# Custom OpenAPI schema customization
def custom_openapi():
    """
    Customize OpenAPI schema with additional information.
    """
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )

    # Add custom information
    openapi_schema["info"]["contact"] = {
        "name": "Web Scraping API Support",
        "email": "support@example.com",
    }

    openapi_schema["info"]["license"] = {
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    }

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": settings.API_KEY_HEADER,
            "description": "API key for authentication"
        },
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "API Key",
            "description": "Bearer token authentication"
        }
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


# Override the default OpenAPI schema
app.openapi = custom_openapi


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.RELOAD,
        workers=1,  # Use 1 worker for development
        log_level=settings.LOG_LEVEL.lower(),
    )

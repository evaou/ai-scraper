"""
Configuration management using Pydantic BaseSettings.

This module handles all environment variable configuration for the application.
"""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration settings for the web scraping API."""

    # Project information
    PROJECT_NAME: str = Field(default="Web Scraping API", description="Project name")
    PROJECT_VERSION: str = Field(default="1.0.0", description="Project version")
    API_V1_STR: str = Field(default="/api/v1", description="API v1 prefix")

    # Database Configuration
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:password@db:5432/scraper",
        description="PostgreSQL database URL"
    )
    POSTGRES_DB: str = Field(default="scraper", description="PostgreSQL database name")
    POSTGRES_USER: str = Field(default="postgres", description="PostgreSQL username")
    POSTGRES_PASSWORD: str = Field(default="password", description="PostgreSQL password")

    # Database Pool Settings
    DB_POOL_SIZE: int = Field(default=10, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=0, description="Database connection pool max overflow")
    DB_POOL_PRE_PING: bool = Field(default=True, description="Enable database connection pre-ping")
    DB_ECHO: bool = Field(default=False, description="Enable SQL query logging")

    # Redis Configuration
    REDIS_URL: str = Field(
        default="redis://redis:6379/0",
        description="Redis connection URL"
    )
    REDIS_HOST: str = Field(default="redis", description="Redis host")
    REDIS_PORT: int = Field(default=6379, description="Redis port")
    REDIS_PASSWORD: str | None = Field(default=None, description="Redis password")
    REDIS_DB: int = Field(default=0, description="Redis database number")
    REDIS_POOL_SIZE: int = Field(default=10, description="Redis connection pool size")
    REDIS_POOL_MAX_CONNECTIONS: int = Field(default=20, description="Redis max connections")

    # API Configuration
    API_HOST: str = Field(default="0.0.0.0", description="API server host")
    API_PORT: int = Field(default=8000, description="API server port")
    API_WORKERS: int = Field(default=1, description="Number of API workers")
    API_KEY_REQUIRED: bool = Field(default=False, description="Whether API key is required")
    CORS_ORIGINS: list[str] = Field(default=["*"], description="CORS allowed origins")

    # Authentication & Security
    JWT_SECRET_KEY: str = Field(
        default="dev-secret-key-change-in-production",
        description="JWT secret key"
    )
    API_KEY_HEADER: str = Field(default="X-API-Key", description="API key header name")

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, description="Rate limit per minute")
    RATE_LIMIT_PER_HOUR: int = Field(default=1000, description="Rate limit per hour")

    # Scraping Configuration
    SCRAPE_TIMEOUT: int = Field(default=30, description="Default scraping timeout")
    WORKER_CONCURRENCY: int = Field(default=3, description="Worker concurrency")
    MAX_CONTENT_SIZE: int = Field(default=10485760, description="Maximum content size")
    SCREENSHOT_ENABLED: bool = Field(default=True, description="Enable screenshots")
    EXTRACT_LINKS_ENABLED: bool = Field(default=True, description="Enable link extraction")

    # Playwright browser settings
    PLAYWRIGHT_BROWSER: Literal["chromium", "firefox", "webkit"] = Field(
        default="chromium",
        description="Browser engine to use for scraping"
    )

    headless: bool = Field(
        default=True,
        description="Whether to run browser in headless mode"
    )

    # User agents for browser rotation
    USER_AGENTS: list[str] = Field(
        default=[
            # Chrome on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            # Chrome on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            # Chrome on Linux
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            # Firefox on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
            # Firefox on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
            # Safari on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1.2 Safari/605.1.15",
        ],
        description="List of user agents for browser rotation"
    )

    # Cache Configuration
    CACHE_TTL: int = Field(default=3600, description="Cache TTL in seconds")
    JOB_STATUS_TTL: int = Field(default=86400, description="Job status TTL in seconds")
    RESULT_CACHE_TTL: int = Field(default=86400, description="Result cache TTL")

    # Worker Configuration
    CELERY_BROKER_URL: str = Field(
        default="redis://redis:6379/1",
        description="Celery broker URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://redis:6379/2",
        description="Celery result backend URL"
    )
    CELERY_WORKER_CONCURRENCY: int = Field(default=2, description="Celery worker concurrency")

    # Concurrency settings (legacy)
    max_concurrency: int = Field(
        default=3,
        description="Maximum number of concurrent browser instances"
    )

    # Retry settings
    max_retries: int = Field(
        default=3,
        description="Maximum number of retry attempts for failed requests"
    )

    backoff_base: float = Field(
        default=1.0,
        description="Base delay in seconds for exponential backoff"
    )

    backoff_max: float = Field(
        default=30.0,
        description="Maximum delay in seconds for exponential backoff"
    )

    # Timeout settings
    default_timeout: int = Field(
        default=30,
        description="Default timeout in seconds for page loading"
    )

    navigation_timeout: int = Field(
        default=30,
        description="Timeout in seconds for page navigation"
    )

    # Development
    DEBUG: bool = Field(default=True, description="Enable debug mode")
    RELOAD: bool = Field(default=False, description="Enable auto-reload")
    ENABLE_DOCS: bool = Field(default=True, description="Expose interactive API docs even when DEBUG is false")

    # Health Check Configuration
    HEALTH_CHECK_TIMEOUT: int = Field(default=5, description="Health check timeout in seconds")

    # Logging settings
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging level"
    )
    LOG_FORMAT: str = Field(default="json", description="Logging format")

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


settings = get_settings()

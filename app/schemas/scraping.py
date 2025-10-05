"""Pydantic schemas for scraping API."""
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, validator


class ScrapingOptions(BaseModel):
    """Options for scraping configuration."""
    wait_for_selector: str | None = Field(None, description="CSS selector to wait for before scraping")
    wait_time: int | None = Field(None, ge=0, le=30, description="Time to wait in seconds (0-30)")
    screenshot: bool = Field(False, description="Take screenshot of the page")
    extract_links: bool = Field(False, description="Extract all links from the page")
    extract_images: bool = Field(False, description="Extract all image URLs from the page")
    extract_text: bool = Field(True, description="Extract text content from the page")
    user_agent: str | None = Field(None, description="Custom User-Agent header")
    viewport_width: int = Field(1920, ge=800, le=3840, description="Browser viewport width")
    viewport_height: int = Field(1080, ge=600, le=2160, description="Browser viewport height")
    timeout: int | None = Field(None, ge=5, le=120, description="Request timeout in seconds")
    follow_redirects: bool = Field(True, description="Follow HTTP redirects")
    ignore_https_errors: bool = Field(False, description="Ignore HTTPS certificate errors")
    block_resources: list[str] = Field(default=[], description="Block resource types (image, stylesheet, font, etc.)")


class ScrapeRequest(BaseModel):
    """Request schema for scraping job."""
    url: HttpUrl = Field(..., description="URL to scrape")
    selector: str | None = Field(None, description="CSS selector for content extraction")
    options: ScrapingOptions | None = Field(default_factory=ScrapingOptions, description="Scraping options")
    priority: int = Field(0, ge=0, le=10, description="Job priority (0=normal, 10=highest)")
    scheduled_at: datetime | None = Field(None, description="When to execute the job (UTC)")
    metadata: dict[str, Any] | None = Field(default={}, description="Additional metadata")

    @validator("url")
    def validate_url(cls, v):
        """Validate URL format."""
        url_str = str(v)
        if not url_str.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @validator("selector")
    def validate_selector(cls, v):
        """Validate CSS selector format."""
        if v and len(v.strip()) == 0:
            return None
        return v


class JobStatusEnum(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class ScrapeResponse(BaseModel):
    """Response schema for scraping job creation."""
    job_id: UUID = Field(..., description="Unique job identifier")
    status: JobStatusEnum = Field(..., description="Current job status")
    url: str = Field(..., description="URL being scraped")
    created_at: datetime = Field(..., description="Job creation timestamp")
    estimated_completion: datetime | None = Field(None, description="Estimated completion time")
    priority: int = Field(..., description="Job priority")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class ScrapingResult(BaseModel):
    """Scraped data result."""
    content: str | None = Field(None, description="Extracted text content")
    html: str | None = Field(None, description="Raw HTML content")
    links: list[str] | None = Field(default=[], description="Extracted links")
    images: list[str] | None = Field(default=[], description="Extracted image URLs")
    title: str | None = Field(None, description="Page title")
    meta_description: str | None = Field(None, description="Meta description")
    headings: dict[str, list[str]] | None = Field(default={}, description="Page headings (h1, h2, etc.)")
    forms: list[dict[str, Any]] | None = Field(default=[], description="Form elements found")
    screenshot_url: str | None = Field(None, description="Screenshot URL if requested")


class ScrapingMetadata(BaseModel):
    """Metadata about the scraping process."""
    execution_time: float | None = Field(None, description="Execution time in seconds")
    response_time: int | None = Field(None, description="HTTP response time in milliseconds")
    page_load_time: int | None = Field(None, description="Page load time in milliseconds")
    dom_ready_time: int | None = Field(None, description="DOM ready time in milliseconds")
    final_url: str | None = Field(None, description="Final URL after redirects")
    status_code: int | None = Field(None, description="HTTP status code")
    content_type: str | None = Field(None, description="Content-Type header")
    content_length: int | None = Field(None, description="Content length in bytes")
    browser_info: dict[str, Any] | None = Field(default={}, description="Browser information")
    timestamp: datetime = Field(..., description="Result timestamp")


class JobDetailResponse(BaseModel):
    """Detailed job information response."""
    job_id: UUID = Field(..., description="Unique job identifier")
    status: JobStatusEnum = Field(..., description="Current job status")
    url: str = Field(..., description="URL being scraped")
    selector: str | None = Field(None, description="CSS selector used")
    options: ScrapingOptions | None = Field(None, description="Scraping options")
    priority: int = Field(..., description="Job priority")
    created_at: datetime = Field(..., description="Job creation timestamp")
    started_at: datetime | None = Field(None, description="Job start timestamp")
    completed_at: datetime | None = Field(None, description="Job completion timestamp")
    retry_count: int = Field(..., description="Number of retries attempted")
    max_retries: int = Field(..., description="Maximum retries allowed")
    error_message: str | None = Field(None, description="Error message if failed")
    data: ScrapingResult | None = Field(None, description="Scraped data (if completed)")
    metadata: ScrapingMetadata | None = Field(None, description="Scraping metadata")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class JobListResponse(BaseModel):
    """Response for job listing."""
    jobs: list[JobDetailResponse] = Field(..., description="List of jobs")
    total: int = Field(..., description="Total number of jobs")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")


class JobStatsResponse(BaseModel):
    """Job statistics response."""
    total: int = Field(..., description="Total number of jobs")
    pending: int = Field(..., description="Number of pending jobs")
    running: int = Field(..., description="Number of running jobs")
    completed: int = Field(..., description="Number of completed jobs")
    failed: int = Field(..., description="Number of failed jobs")
    cancelled: int = Field(..., description="Number of cancelled jobs")
    retrying: int = Field(..., description="Number of jobs being retried")
    average_execution_time: float = Field(..., description="Average execution time in seconds")


class ErrorResponse(BaseModel):
    """Error response schema."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="API version")
    uptime: float = Field(..., description="Uptime in seconds")
    checks: dict[str, bool] = Field(..., description="Individual health checks")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class QueueStatsResponse(BaseModel):
    """Queue statistics response."""
    pending: int = Field(..., description="Jobs pending in queue")
    processing: int = Field(..., description="Jobs currently being processed")
    total: int = Field(..., description="Total jobs in queue")
    workers: int = Field(..., description="Number of active workers")


class AdminStatsResponse(BaseModel):
    """Admin statistics response."""
    jobs: JobStatsResponse = Field(..., description="Job statistics")
    queue: QueueStatsResponse = Field(..., description="Queue statistics")
    cache: dict[str, Any] = Field(..., description="Cache statistics")
    system: dict[str, Any] = Field(..., description="System metrics")


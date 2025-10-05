"""Service layer for scraping operations."""
from datetime import datetime
from typing import Any

from app.models.job import Job
from app.schemas.scraping import ScrapingMetadata, ScrapingResult


def create_scraping_result(data: dict[str, Any]) -> ScrapingResult:
    """
    Convert database result data to ScrapingResult schema.

    Args:
        data: Raw data from database result

    Returns:
        ScrapingResult: Structured result data
    """
    return ScrapingResult(
        content=data.get("content"),
        html=data.get("html"),
        links=data.get("links", []),
        images=data.get("images", []),
        title=data.get("title"),
        meta_description=data.get("meta_description"),
        headings=data.get("headings", {}),
        forms=data.get("forms", []),
        screenshot_url=data.get("screenshot_url"),
    )


def create_scraping_metadata(metadata: dict[str, Any], job: Job) -> ScrapingMetadata:
    """
    Convert database metadata and job info to ScrapingMetadata schema.

    Args:
        metadata: Raw metadata from database
        job: Job instance with timing information

    Returns:
        ScrapingMetadata: Structured metadata
    """
    return ScrapingMetadata(
        execution_time=job.execution_time,
        response_time=metadata.get("response_time"),
        page_load_time=metadata.get("page_load_time"),
        dom_ready_time=metadata.get("dom_ready_time"),
        final_url=metadata.get("final_url"),
        status_code=metadata.get("status_code"),
        content_type=metadata.get("content_type"),
        content_length=metadata.get("content_length"),
        browser_info=metadata.get("browser_info", {}),
        timestamp=job.completed_at or datetime.utcnow(),
    )

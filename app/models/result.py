"""Result model for scraping results."""
from typing import Any
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.database_types import JSONType, UUIDType


class Result(Base):
    """Model for scraping results."""

    __tablename__ = "results"

    # Primary key
    id = Column(UUIDType(), primary_key=True, default=uuid4, index=True)

    # Foreign key to job
    job_id = Column(UUIDType(), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)

    # Scraped data (using JSON/JSONB for better performance)
    data = Column(JSONType(), nullable=False, default=dict)

    # Content metadata
    content_type = Column(String(100), nullable=True)
    content_length = Column(Integer, nullable=True)
    size_bytes = Column(Integer, nullable=True)

    # URLs and references
    final_url = Column(String(2048), nullable=True)  # Final URL after redirects
    screenshot_url = Column(String(1024), nullable=True)

    # HTTP response details
    status_code = Column(Integer, nullable=True)
    response_headers = Column(JSONType(), nullable=True, default=dict)

    # Timing information
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    response_time = Column(Integer, nullable=True)  # Response time in milliseconds

    # Additional metadata
    result_metadata = Column(JSONType(), nullable=True, default=dict)

    # Text content for search/indexing
    text_content = Column(Text, nullable=True)

    # Links extracted from page
    links = Column(JSONType(), nullable=True, default=list)

    # Performance metrics
    page_load_time = Column(Integer, nullable=True)  # Page load time in milliseconds
    dom_ready_time = Column(Integer, nullable=True)  # DOM ready time in milliseconds

    # Browser info
    browser_info = Column(JSONType(), nullable=True, default=dict)

    # Additional indexes for performance
    __table_args__ = (
        Index("ix_results_job_created", "job_id", "created_at"),
        # Note: GIN index for JSONB queries only works in PostgreSQL
        # For SQLite, we'll rely on regular JSON indexing capabilities
        Index("ix_results_status_code", "status_code"),
        Index("ix_results_size_bytes", "size_bytes"),
    )

    # Relationships
    job = relationship("Job", back_populates="result")

    def __repr__(self) -> str:
        """String representation of the result."""
        data_preview = str(self.data)[:100] if self.data else "No data"
        return f"<Result(id={self.id}, job_id={self.job_id}, data='{data_preview}...')>"

    @property
    def total_links(self) -> int:
        """Get total number of links extracted."""
        return len(self.links) if self.links else 0

    @property
    def content_size_mb(self) -> float | None:
        """Get content size in megabytes."""
        if self.size_bytes:
            return round(self.size_bytes / (1024 * 1024), 2)
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "id": str(self.id),
            "job_id": str(self.job_id),
            "data": self.data or {},
            "content_type": self.content_type,
            "content_length": self.content_length,
            "size_bytes": self.size_bytes,
            "size_mb": self.content_size_mb,
            "final_url": self.final_url,
            "screenshot_url": self.screenshot_url,
            "status_code": self.status_code,
            "response_headers": self.response_headers or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "response_time": self.response_time,
            "page_load_time": self.page_load_time,
            "dom_ready_time": self.dom_ready_time,
            "text_content": self.text_content,
            "links": self.links or [],
            "total_links": self.total_links,
            "browser_info": self.browser_info or {},
            "metadata": self.result_metadata or {},
        }

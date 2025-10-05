"""Job model for scraping tasks."""
import enum
from typing import Any
from uuid import uuid4

from sqlalchemy import Column, DateTime, Enum, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class JobStatus(enum.Enum):
    """Enum for job status values."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class Job(Base):
    """Model for scraping jobs."""

    __tablename__ = "jobs"

    # Primary key
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)

    # Job details
    url = Column(String(2048), nullable=False, index=True)
    selector = Column(String(500), nullable=True)
    options = Column(JSONB, nullable=True, default=dict)

    # Status and timing
    status = Column(Enum(JobStatus), nullable=False, default=JobStatus.PENDING, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Error handling and retries
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)

    # Priority and scheduling
    priority = Column(Integer, nullable=False, default=0, index=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)

    # API key for authentication (if required)
    api_key_id = Column(PG_UUID(as_uuid=True), nullable=True)

    # Metadata
    job_metadata = Column(JSONB, nullable=True, default=dict)

    # Additional indexes for query optimization
    __table_args__ = (
        Index("ix_jobs_status_created_at", "status", "created_at"),
        Index("ix_jobs_url_hash", func.md5(url)),  # For efficient duplicate URL detection
        Index("ix_jobs_priority_status", "priority", "status"),
    )

    # Relationships
    result = relationship("Result", back_populates="job", uselist=False, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        """String representation of the job."""
        return f"<Job(id={self.id}, url={self.url[:50]}..., status={self.status.value})>"

    @property
    def execution_time(self) -> float | None:
        """Calculate execution time in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def is_terminal(self) -> bool:
        """Check if job is in a terminal state."""
        return self.status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}

    @property
    def can_retry(self) -> bool:
        """Check if job can be retried."""
        return (
            self.status == JobStatus.FAILED
            and self.retry_count < self.max_retries
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert job to dictionary."""
        return {
            "id": str(self.id),
            "url": self.url,
            "selector": self.selector,
            "options": self.options or {},
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "priority": self.priority,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "execution_time": self.execution_time,
            "metadata": self.job_metadata or {},
        }

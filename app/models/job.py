"""Job model for scraping tasks."""
import enum
from typing import Any
from uuid import uuid4

from sqlalchemy import Column, DateTime, Enum, Index, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.database_types import JSONType, UUIDType


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
    
    def __init__(self, **kwargs):
        """Initialize Job with proper defaults."""
        # Set default values if not provided
        if 'status' not in kwargs:
            kwargs['status'] = JobStatus.PENDING
        if 'retry_count' not in kwargs:
            kwargs['retry_count'] = 0
        if 'max_retries' not in kwargs:
            kwargs['max_retries'] = 3
        if 'priority' not in kwargs:
            kwargs['priority'] = 0
        if 'options' not in kwargs:
            kwargs['options'] = {}
        if 'job_metadata' not in kwargs:
            kwargs['job_metadata'] = {}
        
        super().__init__(**kwargs)

    # Primary key
    id = Column(UUIDType(), primary_key=True, default=uuid4, index=True)

    # Job details
    url = Column(String(2048), nullable=False, index=True)
    selector = Column(String(500), nullable=True)
    options = Column(JSONType(), nullable=True, default=dict)

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
    api_key_id = Column(UUIDType(), nullable=True)

    # Metadata
    job_metadata = Column(JSONType(), nullable=True, default=dict)

    # Additional indexes for query optimization
    __table_args__ = (
        Index("ix_jobs_status_created_at", "status", "created_at"),
        # Note: MD5 index for duplicate URL detection only works in PostgreSQL
        # For SQLite, we'll rely on the regular url index
        Index("ix_jobs_priority_status", "priority", "status"),
    )

    # Relationships
    result = relationship("Result", back_populates="job", uselist=False, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        """String representation of the job."""
        status_value = self.status.value if self.status else 'unknown'
        return f"<Job(id={self.id}, url={self.url[:50]}..., status={status_value})>"

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
            "status": self.status.value if self.status else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "retry_count": self.retry_count if self.retry_count is not None else 0,
            "max_retries": self.max_retries if self.max_retries is not None else 3,
            "priority": self.priority if self.priority is not None else 0,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "execution_time": self.execution_time,
            "metadata": self.job_metadata or {},
        }

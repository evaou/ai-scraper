"""Unit tests for Job model."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.models.job import Job, JobStatus
from tests.fixtures.factories import JobFactory, create_job


class TestJobModel:
    """Test cases for Job model."""
    
    def test_job_creation_with_defaults(self):
        """Test creating a job with default values."""
        job = Job(url="https://example.com")
        
        assert job.url == "https://example.com"
        assert job.status == JobStatus.PENDING
        assert job.retry_count == 0
        assert job.max_retries == 3
        assert job.priority == 0
        assert job.selector is None
        assert job.options == {}
        assert job.error_message is None
        assert job.started_at is None
        assert job.completed_at is None
    
    def test_job_creation_with_custom_values(self):
        """Test creating a job with custom values."""
        custom_options = {"screenshot": True, "timeout": 60}
        custom_metadata = {"client": "test", "version": "1.0"}
        
        job = Job(
            url="https://test.com",
            selector=".content",
            options=custom_options,
            priority=5,
            max_retries=5,
            job_metadata=custom_metadata
        )
        
        assert job.url == "https://test.com"
        assert job.selector == ".content"
        assert job.options == custom_options
        assert job.priority == 5
        assert job.max_retries == 5
        assert job.job_metadata == custom_metadata
    
    def test_job_status_enum_values(self):
        """Test that all JobStatus enum values are valid."""
        valid_statuses = [
            JobStatus.PENDING,
            JobStatus.RUNNING,
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
            JobStatus.RETRYING
        ]
        
        for status in valid_statuses:
            job = Job(url="https://example.com", status=status)
            assert job.status == status
    
    def test_execution_time_calculation(self):
        """Test execution time calculation."""
        job = Job(url="https://example.com")
        
        # No execution time when not started
        assert job.execution_time is None
        
        # No execution time when started but not completed
        job.started_at = datetime.utcnow()
        assert job.execution_time is None
        
        # Execution time when both started and completed
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(seconds=5)
        
        job.started_at = start_time
        job.completed_at = end_time
        
        assert job.execution_time == 5.0
    
    def test_is_terminal_property(self):
        """Test is_terminal property for different job statuses."""
        job = Job(url="https://example.com")
        
        # Terminal states
        terminal_states = [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]
        for status in terminal_states:
            job.status = status
            assert job.is_terminal is True
        
        # Non-terminal states
        non_terminal_states = [JobStatus.PENDING, JobStatus.RUNNING, JobStatus.RETRYING]
        for status in non_terminal_states:
            job.status = status
            assert job.is_terminal is False
    
    def test_can_retry_property(self):
        """Test can_retry property logic."""
        job = Job(url="https://example.com", max_retries=3)
        
        # Cannot retry if not failed
        job.status = JobStatus.PENDING
        job.retry_count = 0
        assert job.can_retry is False
        
        job.status = JobStatus.RUNNING
        assert job.can_retry is False
        
        job.status = JobStatus.COMPLETED
        assert job.can_retry is False
        
        # Can retry if failed and under max retries
        job.status = JobStatus.FAILED
        job.retry_count = 0
        assert job.can_retry is True
        
        job.retry_count = 2
        assert job.can_retry is True
        
        # Cannot retry if at max retries
        job.retry_count = 3
        assert job.can_retry is False
        
        job.retry_count = 4
        assert job.can_retry is False
    
    def test_to_dict_method(self):
        """Test converting job to dictionary."""
        job_id = uuid4()
        now = datetime.utcnow()
        
        job = Job(
            id=job_id,
            url="https://example.com",
            selector=".content",
            options={"screenshot": True},
            status=JobStatus.COMPLETED,
            created_at=now,
            started_at=now,
            completed_at=now + timedelta(seconds=10),
            error_message=None,
            retry_count=1,
            max_retries=3,
            priority=2,
            job_metadata={"test": "value"}
        )
        
        job_dict = job.to_dict()
        
        expected_keys = {
            "id", "url", "selector", "options", "status", 
            "created_at", "started_at", "completed_at", 
            "error_message", "retry_count", "max_retries", 
            "priority", "scheduled_at", "execution_time", "metadata"
        }
        
        assert set(job_dict.keys()) == expected_keys
        assert job_dict["id"] == str(job_id)
        assert job_dict["url"] == "https://example.com"
        assert job_dict["selector"] == ".content"
        assert job_dict["options"] == {"screenshot": True}
        assert job_dict["status"] == "completed"
        assert job_dict["retry_count"] == 1
        assert job_dict["max_retries"] == 3
        assert job_dict["priority"] == 2
        assert job_dict["metadata"] == {"test": "value"}
        assert job_dict["execution_time"] == 10.0
    
    def test_to_dict_with_none_values(self):
        """Test to_dict with None values."""
        job = Job(url="https://example.com")
        job_dict = job.to_dict()
        
        # Check that None values are handled correctly
        assert job_dict["selector"] is None
        assert job_dict["error_message"] is None
        assert job_dict["scheduled_at"] is None
        assert job_dict["execution_time"] is None
        assert job_dict["started_at"] is None
        assert job_dict["completed_at"] is None
    
    def test_job_repr(self):
        """Test job string representation."""
        job_id = uuid4()
        job = Job(
            id=job_id,
            url="https://very-long-url-that-should-be-truncated.com/with/many/path/segments",
            status=JobStatus.RUNNING
        )
        
        repr_str = repr(job)
        
        assert f"<Job(id={job_id}" in repr_str
        assert "status=running" in repr_str
        # URL should be truncated to 50 chars
        assert "https://very-long-url-that-should-be-truncated" in repr_str
        assert "..." in repr_str


class TestJobWithFactory:
    """Test Job model using factory patterns."""
    
    def test_create_job_with_factory(self):
        """Test creating jobs using factory."""
        job = create_job()
        
        assert isinstance(job.url, str)
        assert job.url.startswith("http")
        assert job.status == JobStatus.PENDING
        assert isinstance(job.priority, int)
        assert 0 <= job.priority <= 5
    
    def test_create_multiple_jobs_with_factory(self):
        """Test creating multiple unique jobs."""
        jobs = [create_job() for _ in range(5)]
        
        # All jobs should have different URLs
        urls = [job.url for job in jobs]
        assert len(set(urls)) == 5
        
        # All should be valid Job instances
        for job in jobs:
            assert isinstance(job, Job)
            assert job.status == JobStatus.PENDING
    
    def test_factory_override_values(self):
        """Test factory with custom override values."""
        custom_url = "https://custom.example.com"
        custom_priority = 10
        
        job = create_job(url=custom_url, priority=custom_priority)
        
        assert job.url == custom_url
        assert job.priority == custom_priority
    
    @pytest.mark.parametrize("status", [
        JobStatus.PENDING,
        JobStatus.RUNNING,
        JobStatus.COMPLETED,
        JobStatus.FAILED,
        JobStatus.CANCELLED,
        JobStatus.RETRYING
    ])
    def test_job_with_different_statuses(self, status):
        """Test job creation with different statuses."""
        job = create_job(status=status)
        assert job.status == status
    
    def test_job_with_complex_options(self):
        """Test job with complex options."""
        options = {
            "screenshot": True,
            "extract_links": True,
            "extract_images": False,
            "timeout": 45,
            "viewport_width": 1920,
            "viewport_height": 1080,
            "user_agent": "Custom User Agent"
        }
        
        job = create_job(options=options)
        assert job.options == options
    
    def test_job_metadata_handling(self):
        """Test job metadata is properly handled."""
        metadata = {
            "client_id": "test-client",
            "request_source": "api",
            "tags": ["urgent", "marketing"],
            "custom_fields": {
                "department": "engineering",
                "cost_center": "12345"
            }
        }
        
        job = create_job(job_metadata=metadata)
        assert job.job_metadata == metadata
    
    def test_job_validation_constraints(self):
        """Test job field constraints and validation."""
        # URL should be required (this would be enforced by the database)
        job = Job(url="https://example.com")
        assert job.url is not None
        
        # Priority should have reasonable bounds in real usage
        job = create_job(priority=0)
        assert job.priority >= 0
        
        job = create_job(priority=10)
        assert job.priority <= 10
        
        # Retry count should start at 0
        job = Job(url="https://example.com")
        assert job.retry_count == 0
        
        # Max retries should be positive
        job = create_job(max_retries=5)
        assert job.max_retries > 0
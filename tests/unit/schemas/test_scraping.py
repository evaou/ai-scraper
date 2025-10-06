"""Unit tests for scraping schemas."""

import pytest
from datetime import datetime
from uuid import uuid4
from pydantic import ValidationError

from app.schemas.scraping import (
    ScrapingOptions, ScrapeRequest, ScrapingResult, 
    ScrapingMetadata, JobDetailResponse, JobStatusEnum,
    ScrapeResponse, JobListResponse, JobStatsResponse,
    ErrorResponse, HealthResponse, QueueStatsResponse,
    AdminStatsResponse
)
from tests.fixtures.factories import (
    create_scrape_request, create_scraping_result, 
    create_scraping_metadata
)


class TestScrapingOptions:
    """Test cases for ScrapingOptions schema."""
    
    def test_scraping_options_defaults(self):
        """Test ScrapingOptions with default values."""
        options = ScrapingOptions()
        
        assert options.wait_for_selector is None
        assert options.wait_time is None
        assert options.screenshot is False
        assert options.extract_links is False
        assert options.extract_images is False
        assert options.extract_text is True
        assert options.user_agent is None
        assert options.viewport_width == 1920
        assert options.viewport_height == 1080
        assert options.timeout is None
        assert options.follow_redirects is True
        assert options.ignore_https_errors is False
        assert options.block_resources == []
    
    def test_scraping_options_with_custom_values(self):
        """Test ScrapingOptions with custom values."""
        options = ScrapingOptions(
            wait_for_selector=".content",
            wait_time=5,
            screenshot=True,
            extract_links=True,
            extract_images=True,
            extract_text=False,
            user_agent="Custom Agent",
            viewport_width=1440,
            viewport_height=900,
            timeout=60,
            follow_redirects=False,
            ignore_https_errors=True,
            block_resources=["image", "font"]
        )
        
        assert options.wait_for_selector == ".content"
        assert options.wait_time == 5
        assert options.screenshot is True
        assert options.extract_links is True
        assert options.extract_images is True
        assert options.extract_text is False
        assert options.user_agent == "Custom Agent"
        assert options.viewport_width == 1440
        assert options.viewport_height == 900
        assert options.timeout == 60
        assert options.follow_redirects is False
        assert options.ignore_https_errors is True
        assert options.block_resources == ["image", "font"]
    
    def test_scraping_options_validation(self):
        """Test ScrapingOptions validation."""
        # Valid wait_time range
        ScrapingOptions(wait_time=0)
        ScrapingOptions(wait_time=30)
        
        # Invalid wait_time
        with pytest.raises(ValidationError):
            ScrapingOptions(wait_time=-1)
        with pytest.raises(ValidationError):
            ScrapingOptions(wait_time=31)
        
        # Valid viewport dimensions
        ScrapingOptions(viewport_width=800, viewport_height=600)
        ScrapingOptions(viewport_width=3840, viewport_height=2160)
        
        # Invalid viewport dimensions
        with pytest.raises(ValidationError):
            ScrapingOptions(viewport_width=799)
        with pytest.raises(ValidationError):
            ScrapingOptions(viewport_width=3841)
        with pytest.raises(ValidationError):
            ScrapingOptions(viewport_height=599)
        with pytest.raises(ValidationError):
            ScrapingOptions(viewport_height=2161)
        
        # Valid timeout range
        ScrapingOptions(timeout=5)
        ScrapingOptions(timeout=120)
        
        # Invalid timeout
        with pytest.raises(ValidationError):
            ScrapingOptions(timeout=4)
        with pytest.raises(ValidationError):
            ScrapingOptions(timeout=121)


class TestScrapeRequest:
    """Test cases for ScrapeRequest schema."""
    
    def test_scrape_request_minimal(self):
        """Test ScrapeRequest with minimal required fields."""
        request = ScrapeRequest(url="https://example.com")
        
        assert str(request.url) == "https://example.com/"
        assert request.selector is None
        assert isinstance(request.options, ScrapingOptions)
        assert request.priority == 0
        assert request.scheduled_at is None
        assert request.metadata == {}
    
    def test_scrape_request_full(self):
        """Test ScrapeRequest with all fields."""
        now = datetime.utcnow()
        options = ScrapingOptions(screenshot=True, timeout=45)
        metadata = {"client": "test", "version": "1.0"}
        
        request = ScrapeRequest(
            url="https://test.example.com",
            selector=".main-content",
            options=options,
            priority=5,
            scheduled_at=now,
            metadata=metadata
        )
        
        assert str(request.url) == "https://test.example.com/"
        assert request.selector == ".main-content"
        assert request.options == options
        assert request.priority == 5
        assert request.scheduled_at == now
        assert request.metadata == metadata
    
    def test_scrape_request_url_validation(self):
        """Test URL validation in ScrapeRequest."""
        # Valid URLs
        ScrapeRequest(url="https://example.com")
        ScrapeRequest(url="http://example.com")
        ScrapeRequest(url="https://sub.example.com/path?query=value")
        
        # Invalid URLs
        with pytest.raises(ValidationError):
            ScrapeRequest(url="not-a-url")
        with pytest.raises(ValidationError):
            ScrapeRequest(url="ftp://example.com")
        with pytest.raises(ValidationError):
            ScrapeRequest(url="javascript:alert('test')")
    
    def test_scrape_request_selector_validation(self):
        """Test CSS selector validation."""
        # Valid selectors
        request = ScrapeRequest(url="https://example.com", selector="h1")
        assert request.selector == "h1"
        
        request = ScrapeRequest(url="https://example.com", selector=".content")
        assert request.selector == ".content"
        
        # Empty selector becomes None
        request = ScrapeRequest(url="https://example.com", selector="")
        assert request.selector == ""
        
        request = ScrapeRequest(url="https://example.com", selector="   ")
        assert request.selector is None
    
    def test_scrape_request_priority_validation(self):
        """Test priority field validation."""
        # Valid priorities
        ScrapeRequest(url="https://example.com", priority=0)
        ScrapeRequest(url="https://example.com", priority=5)
        ScrapeRequest(url="https://example.com", priority=10)
        
        # Invalid priorities
        with pytest.raises(ValidationError):
            ScrapeRequest(url="https://example.com", priority=-1)
        with pytest.raises(ValidationError):
            ScrapeRequest(url="https://example.com", priority=11)
    
    def test_scrape_request_with_factory(self):
        """Test ScrapeRequest using factory."""
        request = create_scrape_request()
        
        assert isinstance(request, ScrapeRequest)
        assert str(request.url).startswith("http")
        assert isinstance(request.options, ScrapingOptions)
        assert 0 <= request.priority <= 10
        assert isinstance(request.metadata, dict)


class TestScrapingResult:
    """Test cases for ScrapingResult schema."""
    
    def test_scraping_result_defaults(self):
        """Test ScrapingResult with default values."""
        result = ScrapingResult()
        
        assert result.content is None
        assert result.html is None
        assert result.links == []
        assert result.images == []
        assert result.title is None
        assert result.meta_description is None
        assert result.headings == {}
        assert result.forms == []
        assert result.screenshot_url is None
    
    def test_scraping_result_full(self):
        """Test ScrapingResult with all fields."""
        result = ScrapingResult(
            content="Page content",
            html="<html><body>Test</body></html>",
            links=["https://example.com/page1"],
            images=["https://example.com/image.jpg"],
            title="Test Page",
            meta_description="Test description",
            headings={"h1": ["Title"], "h2": ["Subtitle"]},
            forms=[{"action": "/submit", "method": "POST"}],
            screenshot_url="https://example.com/screenshot.png"
        )
        
        assert result.content == "Page content"
        assert result.html == "<html><body>Test</body></html>"
        assert result.links == ["https://example.com/page1"]
        assert result.images == ["https://example.com/image.jpg"]
        assert result.title == "Test Page"
        assert result.meta_description == "Test description"
        assert result.headings == {"h1": ["Title"], "h2": ["Subtitle"]}
        assert result.forms == [{"action": "/submit", "method": "POST"}]
        assert result.screenshot_url == "https://example.com/screenshot.png"
    
    def test_scraping_result_with_factory(self):
        """Test ScrapingResult using factory."""
        result = create_scraping_result()
        
        assert isinstance(result, ScrapingResult)
        if result.content:
            assert isinstance(result.content, str)
        if result.links:
            assert isinstance(result.links, list)
            for link in result.links:
                assert isinstance(link, str)


class TestScrapingMetadata:
    """Test cases for ScrapingMetadata schema."""
    
    def test_scraping_metadata_required_field(self):
        """Test ScrapingMetadata with required timestamp field."""
        now = datetime.utcnow()
        metadata = ScrapingMetadata(timestamp=now)
        
        assert metadata.timestamp == now
        assert metadata.execution_time is None
        assert metadata.response_time is None
        assert metadata.final_url is None
        assert metadata.browser_info == {}
    
    def test_scraping_metadata_full(self):
        """Test ScrapingMetadata with all fields."""
        now = datetime.utcnow()
        browser_info = {"name": "chromium", "version": "120.0.0.0"}
        
        metadata = ScrapingMetadata(
            execution_time=5.5,
            response_time=1200,
            page_load_time=2500,
            dom_ready_time=800,
            final_url="https://final.example.com",
            status_code=200,
            content_type="text/html",
            content_length=15000,
            browser_info=browser_info,
            timestamp=now
        )
        
        assert metadata.execution_time == 5.5
        assert metadata.response_time == 1200
        assert metadata.page_load_time == 2500
        assert metadata.dom_ready_time == 800
        assert metadata.final_url == "https://final.example.com"
        assert metadata.status_code == 200
        assert metadata.content_type == "text/html"
        assert metadata.content_length == 15000
        assert metadata.browser_info == browser_info
        assert metadata.timestamp == now
    
    def test_scraping_metadata_with_factory(self):
        """Test ScrapingMetadata using factory."""
        metadata = create_scraping_metadata()
        
        assert isinstance(metadata, ScrapingMetadata)
        assert isinstance(metadata.timestamp, datetime)
        if metadata.execution_time:
            assert metadata.execution_time > 0
        if metadata.status_code:
            assert isinstance(metadata.status_code, int)


class TestJobStatusEnum:
    """Test cases for JobStatusEnum."""
    
    def test_job_status_enum_values(self):
        """Test all JobStatusEnum values."""
        expected_values = {
            "pending", "running", "completed", 
            "failed", "cancelled", "retrying"
        }
        
        actual_values = {status.value for status in JobStatusEnum}
        assert actual_values == expected_values
    
    def test_job_status_enum_string_inheritance(self):
        """Test that JobStatusEnum inherits from str."""
        status = JobStatusEnum.PENDING
        
        assert isinstance(status, str)
        assert status == "pending"
        assert str(status) == "JobStatusEnum.PENDING"


class TestScrapeResponse:
    """Test cases for ScrapeResponse schema."""
    
    def test_scrape_response_creation(self):
        """Test ScrapeResponse creation."""
        job_id = uuid4()
        now = datetime.utcnow()
        
        response = ScrapeResponse(
            job_id=job_id,
            status=JobStatusEnum.PENDING,
            url="https://example.com",
            created_at=now,
            priority=5
        )
        
        assert response.job_id == job_id
        assert response.status == JobStatusEnum.PENDING
        assert response.url == "https://example.com"
        assert response.created_at == now
        assert response.priority == 5
        assert response.estimated_completion is None
    
    def test_scrape_response_json_encoding(self):
        """Test ScrapeResponse JSON encoding."""
        job_id = uuid4()
        now = datetime.utcnow()
        
        response = ScrapeResponse(
            job_id=job_id,
            status=JobStatusEnum.COMPLETED,
            url="https://example.com",
            created_at=now,
            priority=0
        )
        
        json_data = response.dict()
        
        assert json_data["job_id"] == job_id  # UUID object in dict
        assert json_data["status"] == "completed"
        assert json_data["created_at"] == now  # datetime object in dict


class TestJobDetailResponse:
    """Test cases for JobDetailResponse schema."""
    
    def test_job_detail_response_minimal(self):
        """Test JobDetailResponse with minimal fields."""
        job_id = uuid4()
        now = datetime.utcnow()
        
        response = JobDetailResponse(
            job_id=job_id,
            status=JobStatusEnum.PENDING,
            url="https://example.com",
            priority=0,
            created_at=now,
            retry_count=0,
            max_retries=3
        )
        
        assert response.job_id == job_id
        assert response.status == JobStatusEnum.PENDING
        assert response.url == "https://example.com"
        assert response.priority == 0
        assert response.created_at == now
        assert response.retry_count == 0
        assert response.max_retries == 3
        assert response.selector is None
        assert response.data is None
        assert response.metadata is None
    
    def test_job_detail_response_with_data(self):
        """Test JobDetailResponse with result data."""
        job_id = uuid4()
        now = datetime.utcnow()
        
        result_data = ScrapingResult(
            content="Test content",
            title="Test Page"
        )
        
        result_metadata = ScrapingMetadata(
            execution_time=5.0,
            timestamp=now
        )
        
        response = JobDetailResponse(
            job_id=job_id,
            status=JobStatusEnum.COMPLETED,
            url="https://example.com",
            priority=0,
            created_at=now,
            started_at=now,
            completed_at=now,
            retry_count=0,
            max_retries=3,
            data=result_data,
            metadata=result_metadata
        )
        
        assert response.status == JobStatusEnum.COMPLETED
        assert response.data == result_data
        assert response.metadata == result_metadata
        assert response.started_at == now
        assert response.completed_at == now


class TestErrorResponse:
    """Test cases for ErrorResponse schema."""
    
    def test_error_response_minimal(self):
        """Test ErrorResponse with minimal fields."""
        error = ErrorResponse(
            error="ValidationError",
            message="Invalid input data"
        )
        
        assert error.error == "ValidationError"
        assert error.message == "Invalid input data"
        assert error.details is None
        assert isinstance(error.timestamp, datetime)
    
    def test_error_response_with_details(self):
        """Test ErrorResponse with error details."""
        now = datetime.utcnow()
        details = {"field": "url", "issue": "Invalid format"}
        
        error = ErrorResponse(
            error="ValidationError",
            message="Invalid input data",
            details=details,
            timestamp=now
        )
        
        assert error.error == "ValidationError"
        assert error.message == "Invalid input data"
        assert error.details == details
        assert error.timestamp == now


class TestStatsResponses:
    """Test cases for statistics response schemas."""
    
    def test_job_stats_response(self):
        """Test JobStatsResponse schema."""
        stats = JobStatsResponse(
            total=100,
            pending=10,
            running=5,
            completed=80,
            failed=3,
            cancelled=2,
            retrying=0,
            average_execution_time=25.5
        )
        
        assert stats.total == 100
        assert stats.pending == 10
        assert stats.running == 5
        assert stats.completed == 80
        assert stats.failed == 3
        assert stats.cancelled == 2
        assert stats.retrying == 0
        assert stats.average_execution_time == 25.5
    
    def test_queue_stats_response(self):
        """Test QueueStatsResponse schema."""
        stats = QueueStatsResponse(
            pending=15,
            processing=3,
            total=18,
            workers=2
        )
        
        assert stats.pending == 15
        assert stats.processing == 3
        assert stats.total == 18
        assert stats.workers == 2
    
    def test_admin_stats_response(self):
        """Test AdminStatsResponse schema."""
        job_stats = JobStatsResponse(
            total=50, pending=5, running=2, completed=40,
            failed=2, cancelled=1, retrying=0, average_execution_time=15.0
        )
        
        queue_stats = QueueStatsResponse(
            pending=5, processing=2, total=7, workers=2
        )
        
        cache_info = {"hits": 1000, "misses": 50, "hit_rate": 0.95}
        system_info = {"memory_usage": "512MB", "cpu_usage": "15%"}
        
        admin_stats = AdminStatsResponse(
            jobs=job_stats,
            queue=queue_stats,
            cache=cache_info,
            system=system_info
        )
        
        assert admin_stats.jobs == job_stats
        assert admin_stats.queue == queue_stats
        assert admin_stats.cache == cache_info
        assert admin_stats.system == system_info


class TestHealthResponse:
    """Test cases for HealthResponse schema."""
    
    def test_health_response(self):
        """Test HealthResponse schema."""
        now = datetime.utcnow()
        checks = {"database": True, "redis": True, "worker": False}
        
        health = HealthResponse(
            status="degraded",
            timestamp=now,
            version="1.0.0",
            uptime=3600.5,
            checks=checks
        )
        
        assert health.status == "degraded"
        assert health.timestamp == now
        assert health.version == "1.0.0"
        assert health.uptime == 3600.5
        assert health.checks == checks
"""Integration tests for API endpoints."""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock

from tests.fixtures.factories import create_scrape_request


@pytest.mark.integration
class TestScrapingEndpoints:
    """Integration tests for scraping endpoints."""
    
    @pytest.mark.asyncio
    async def test_submit_scrape_job_success(self, client: AsyncClient, sample_scrape_request):
        """Test successful scraping job submission."""
        response = await client.post("/api/v1/scrape", json=sample_scrape_request)
        
        assert response.status_code == 202
        data = response.json()
        
        assert "job_id" in data
        assert "status" in data
        assert "url" in data
        assert "created_at" in data
        assert data["status"] == "pending"
        assert data["url"] == sample_scrape_request["url"]
    
    @pytest.mark.asyncio
    async def test_submit_scrape_job_invalid_url(self, client: AsyncClient):
        """Test scraping job submission with invalid URL."""
        invalid_request = {
            "url": "not-a-valid-url",
            "selector": "h1"
        }
        
        response = await client.post("/api/v1/scrape", json=invalid_request)
        
        assert response.status_code == 422
        data = response.json()
        assert "error" in data or "detail" in data
    
    @pytest.mark.asyncio
    async def test_submit_scrape_job_missing_url(self, client: AsyncClient):
        """Test scraping job submission without URL."""
        invalid_request = {
            "selector": "h1",
            "priority": 1
        }
        
        response = await client.post("/api/v1/scrape", json=invalid_request)
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_submit_scrape_job_with_options(self, client: AsyncClient):
        """Test scraping job submission with advanced options."""
        request_data = {
            "url": "https://example.com",
            "selector": ".content",
            "options": {
                "screenshot": True,
                "extract_links": True,
                "extract_images": True,
                "timeout": 45,
                "viewport_width": 1440,
                "viewport_height": 900,
                "user_agent": "Custom Test Agent"
            },
            "priority": 8,
            "metadata": {
                "client": "integration-test",
                "test_run": True
            }
        }
        
        response = await client.post("/api/v1/scrape", json=request_data)
        
        assert response.status_code == 202
        data = response.json()
        
        assert data["priority"] == 8
        assert data["url"] == "https://example.com"
    
    @pytest.mark.asyncio
    async def test_get_job_details_not_found(self, client: AsyncClient):
        """Test getting job details for non-existent job."""
        fake_job_id = "00000000-0000-0000-0000-000000000000"
        
        response = await client.get(f"/api/v1/scrape/{fake_job_id}")
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_job_details_invalid_uuid(self, client: AsyncClient):
        """Test getting job details with invalid UUID format."""
        invalid_uuid = "not-a-uuid"
        
        response = await client.get(f"/api/v1/scrape/{invalid_uuid}")
        
        assert response.status_code in [422, 400]  # Depends on FastAPI validation
    
    @pytest.mark.asyncio
    async def test_list_jobs_empty(self, client: AsyncClient):
        """Test listing jobs when database is empty."""
        response = await client.get("/api/v1/results")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "jobs" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert "pages" in data
        assert data["total"] == 0
        assert data["jobs"] == []
    
    @pytest.mark.asyncio
    async def test_list_jobs_with_pagination(self, client: AsyncClient):
        """Test listing jobs with pagination parameters."""
        response = await client.get("/api/v1/results?page=2&per_page=5")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["page"] == 2
        assert data["per_page"] == 5
    
    @pytest.mark.asyncio 
    async def test_get_job_stats(self, client: AsyncClient):
        """Test getting job statistics."""
        response = await client.get("/api/v1/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        expected_keys = {
            "total", "pending", "running", "completed", 
            "failed", "cancelled", "retrying", "average_execution_time"
        }
        assert set(data.keys()) == expected_keys
        
        # All values should be numeric
        for key, value in data.items():
            if key != "average_execution_time":
                assert isinstance(value, int)
            else:
                assert isinstance(value, (int, float))


@pytest.mark.integration
class TestHealthEndpoints:
    """Integration tests for health check endpoints."""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test main health check endpoint."""
        response = await client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        
        required_keys = {"status", "timestamp", "version", "uptime", "checks"}
        assert set(data.keys()) >= required_keys
        
        # Status should be a string
        assert isinstance(data["status"], str)
        
        # Checks should be a dictionary
        assert isinstance(data["checks"], dict)
        
        # Version should be present
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0
    
    @pytest.mark.asyncio
    async def test_liveness_probe(self, client: AsyncClient):
        """Test Kubernetes-style liveness probe."""
        response = await client.get("/api/v1/health/live")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert data["status"] == "alive"
    
    @pytest.mark.asyncio
    async def test_readiness_probe(self, client: AsyncClient):
        """Test Kubernetes-style readiness probe."""
        response = await client.get("/api/v1/health/ready")
        
        # This might be 200 or 503 depending on dependencies
        assert response.status_code in [200, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
    
    @pytest.mark.asyncio
    async def test_version_endpoint(self, client: AsyncClient):
        """Test version information endpoint."""
        response = await client.get("/api/v1/version")
        
        assert response.status_code == 200
        data = response.json()
        
        expected_keys = {"version", "name", "api_version"}
        assert set(data.keys()) >= expected_keys


@pytest.mark.integration
class TestAdminEndpoints:
    """Integration tests for admin endpoints."""
    
    @pytest.mark.asyncio
    async def test_admin_stats(self, client: AsyncClient):
        """Test admin statistics endpoint."""
        response = await client.get("/api/v1/admin/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        expected_top_keys = {"jobs", "queue", "cache", "system"}
        assert set(data.keys()) >= expected_top_keys
        
        # Jobs stats should have required fields
        jobs_stats = data["jobs"]
        expected_job_keys = {
            "total", "pending", "running", "completed",
            "failed", "cancelled", "retrying", "average_execution_time"
        }
        assert set(jobs_stats.keys()) >= expected_job_keys
        
        # Queue stats should have required fields
        queue_stats = data["queue"]
        expected_queue_keys = {"pending", "processing", "total", "workers"}
        assert set(queue_stats.keys()) >= expected_queue_keys
    
    @pytest.mark.asyncio
    async def test_queue_status(self, client: AsyncClient):
        """Test queue status endpoint."""
        response = await client.get("/api/v1/admin/queue")
        
        assert response.status_code == 200
        data = response.json()
        
        expected_keys = {"pending", "processing", "total", "workers"}
        assert set(data.keys()) >= expected_keys
        
        # All values should be numeric
        for key, value in data.items():
            assert isinstance(value, int)
            assert value >= 0
    
    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, client: AsyncClient):
        """Test Prometheus metrics endpoint."""
        response = await client.get("/api/v1/admin/metrics")
        
        # This endpoint might not be implemented yet
        assert response.status_code in [200, 404, 501]
        
        if response.status_code == 200:
            content = response.text
            # Should be Prometheus format
            assert "scraper_" in content or "HELP" in content or "TYPE" in content


@pytest.mark.integration
class TestRootEndpoints:
    """Integration tests for root and misc endpoints."""
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        """Test root endpoint."""
        response = await client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        expected_keys = {"name", "version", "status", "api_version"}
        assert set(data.keys()) >= expected_keys
        
        assert data["status"] == "running"
        assert isinstance(data["name"], str)
        assert isinstance(data["version"], str)
        assert isinstance(data["api_version"], str)
    
    @pytest.mark.asyncio
    async def test_openapi_docs_accessible(self, client: AsyncClient):
        """Test that OpenAPI documentation is accessible."""
        response = await client.get("/api/v1/docs")
        
        # In debug mode, docs should be available
        # In production, they might be disabled (404)
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            # Should return HTML content
            assert "text/html" in response.headers.get("content-type", "")
    
    @pytest.mark.asyncio
    async def test_openapi_json_accessible(self, client: AsyncClient):
        """Test that OpenAPI JSON schema is accessible."""
        response = await client.get("/api/v1/openapi.json")
        
        # In debug mode, OpenAPI should be available
        # In production, it might be disabled (404)
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "openapi" in data
            assert "info" in data
            assert "paths" in data


@pytest.mark.integration
class TestErrorHandling:
    """Integration tests for error handling."""
    
    @pytest.mark.asyncio
    async def test_invalid_json_payload(self, client: AsyncClient):
        """Test handling of invalid JSON payload."""
        response = await client.post(
            "/api/v1/scrape", 
            content="invalid json{", 
            headers={"content-type": "application/json"}
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_unsupported_media_type(self, client: AsyncClient):
        """Test handling of unsupported media type."""
        response = await client.post(
            "/api/v1/scrape", 
            content="<xml>test</xml>", 
            headers={"content-type": "application/xml"}
        )
        
        assert response.status_code in [422, 415]
    
    @pytest.mark.asyncio
    async def test_method_not_allowed(self, client: AsyncClient):
        """Test method not allowed error."""
        response = await client.patch("/api/v1/scrape")
        
        assert response.status_code == 405
    
    @pytest.mark.asyncio
    async def test_not_found_endpoint(self, client: AsyncClient):
        """Test 404 for non-existent endpoint."""
        response = await client.get("/api/v1/non-existent-endpoint")
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_large_payload_handling(self, client: AsyncClient):
        """Test handling of very large payloads."""
        large_metadata = {f"key_{i}": f"value_{i}" * 1000 for i in range(100)}
        large_request = {
            "url": "https://example.com",
            "metadata": large_metadata
        }
        
        response = await client.post("/api/v1/scrape", json=large_request)
        
        # Should either accept it (202) or reject it (413/422)
        assert response.status_code in [202, 413, 422]
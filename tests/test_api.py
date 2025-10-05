"""API endpoint tests."""
import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def client_with_override():
    """Client with database override for testing."""
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    async def test_health_check(self, client: AsyncClient):
        """Test main health check endpoint."""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "uptime" in data
        assert "checks" in data
    
    async def test_liveness_check(self, client: AsyncClient):
        """Test liveness check endpoint."""
        response = await client.get("/api/v1/health/live")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "alive"
    
    async def test_version_endpoint(self, client: AsyncClient):
        """Test version endpoint."""
        response = await client.get("/api/v1/version")
        assert response.status_code == 200
        
        data = response.json()
        assert "version" in data
        assert "name" in data
        assert "api_version" in data


class TestScrapingEndpoints:
    """Test scraping API endpoints."""
    
    async def test_submit_scrape_job(self, client: AsyncClient, sample_scrape_request):
        """Test submitting a scraping job."""
        response = await client.post("/api/v1/scrape", json=sample_scrape_request)
        assert response.status_code == 202
        
        data = response.json()
        assert "job_id" in data
        assert "status" in data
        assert "url" in data
        assert "created_at" in data
        assert data["status"] == "pending"
    
    async def test_submit_scrape_job_invalid_url(self, client: AsyncClient):
        """Test submitting job with invalid URL."""
        invalid_request = {
            "url": "not-a-url",
            "selector": "h1"
        }
        
        response = await client.post("/api/v1/scrape", json=invalid_request)
        assert response.status_code == 422
    
    async def test_get_job_details_not_found(self, client: AsyncClient):
        """Test getting details for non-existent job."""
        job_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/api/v1/scrape/{job_id}")
        assert response.status_code == 404
    
    async def test_get_job_stats(self, client: AsyncClient):
        """Test getting job statistics."""
        response = await client.get("/api/v1/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "total" in data
        assert "pending" in data
        assert "running" in data
        assert "completed" in data
        assert "failed" in data
        assert "average_execution_time" in data
    
    async def test_list_results(self, client: AsyncClient):
        """Test listing results."""
        response = await client.get("/api/v1/results")
        assert response.status_code == 200
        
        data = response.json()
        assert "jobs" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert "pages" in data


class TestAdminEndpoints:
    """Test admin API endpoints."""
    
    async def test_admin_stats(self, client: AsyncClient):
        """Test admin statistics endpoint."""
        response = await client.get("/api/v1/admin/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "jobs" in data
        assert "queue" in data
        assert "cache" in data
        assert "system" in data
    
    async def test_queue_status(self, client: AsyncClient):
        """Test queue status endpoint."""
        response = await client.get("/api/v1/admin/queue")
        assert response.status_code == 200
        
        data = response.json()
        assert "pending" in data
        assert "processing" in data
        assert "total" in data
        assert "workers" in data
    
    async def test_metrics_endpoint(self, client: AsyncClient):
        """Test Prometheus metrics endpoint."""
        response = await client.get("/api/v1/admin/metrics")
        assert response.status_code == 200
        
        content = response.text
        assert "scraper_jobs_total" in content
        assert "scraper_queue_pending" in content


class TestRootEndpoints:
    """Test root and misc endpoints."""
    
    async def test_root_endpoint(self, client: AsyncClient):
        """Test root endpoint."""
        response = await client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "status" in data
        assert data["status"] == "running"
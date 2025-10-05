"""Load testing for AI Scraper API using Locust."""

import random
import json
from locust import HttpUser, task, between
from faker import Faker

fake = Faker()


class ScraperAPIUser(HttpUser):
    """Simulated user for load testing the scraper API."""
    
    # Wait time between requests (1-3 seconds)
    wait_time = between(1, 3)
    
    def on_start(self):
        """Initialize user session."""
        self.job_ids = []
        self.client.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "LoadTest/1.0"
        })
    
    @task(10)
    def submit_scrape_job(self):
        """Submit a scraping job (most common operation)."""
        # Generate realistic test URLs
        test_urls = [
            "https://httpbin.org/html",
            "https://httpbin.org/json", 
            "https://httpbin.org/status/200",
            "https://example.com",
            "https://httpbin.org/delay/1",
            "https://httpbin.org/headers",
        ]
        
        request_data = {
            "url": random.choice(test_urls),
            "selector": random.choice(["h1", ".content", "#main", "p", None]),
            "options": {
                "extract_text": True,
                "extract_links": random.choice([True, False]),
                "screenshot": random.choice([True, False]),
                "timeout": random.randint(10, 60),
                "viewport_width": random.choice([1920, 1366, 1440]),
                "viewport_height": random.choice([1080, 768, 900])
            },
            "priority": random.randint(0, 10),
            "metadata": {
                "client": "load-test",
                "test_run": True,
                "user_id": fake.uuid4(),
                "timestamp": fake.iso8601()
            }
        }
        
        with self.client.post("/api/v1/scrape", json=request_data, catch_response=True) as response:
            if response.status_code == 202:
                try:
                    data = response.json()
                    job_id = data.get("job_id")
                    if job_id:
                        self.job_ids.append(job_id)
                        # Limit stored job IDs to prevent memory growth
                        if len(self.job_ids) > 50:
                            self.job_ids = self.job_ids[-25:]
                    response.success()
                except (json.JSONDecodeError, KeyError):
                    response.failure("Invalid response format")
            else:
                response.failure(f"Unexpected status code: {response.status_code}")
    
    @task(5)
    def check_job_status(self):
        """Check status of previously submitted jobs."""
        if not self.job_ids:
            return
        
        job_id = random.choice(self.job_ids)
        with self.client.get(f"/api/v1/scrape/{job_id}", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "status" in data:
                        response.success()
                    else:
                        response.failure("Missing status field")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code == 404:
                # Job might not exist yet or was cleaned up
                response.success()
            else:
                response.failure(f"Unexpected status code: {response.status_code}")
    
    @task(3)
    def list_jobs(self):
        """List recent jobs with pagination."""
        params = {
            "page": random.randint(1, 3),
            "per_page": random.randint(5, 20)
        }
        
        with self.client.get("/api/v1/results", params=params, catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    required_keys = {"jobs", "total", "page", "per_page", "pages"}
                    if required_keys.issubset(data.keys()):
                        response.success()
                    else:
                        response.failure("Missing required fields in response")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Unexpected status code: {response.status_code}")
    
    @task(2)
    def get_job_stats(self):
        """Get job statistics."""
        with self.client.get("/api/v1/stats", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    expected_keys = {
                        "total", "pending", "running", "completed", 
                        "failed", "cancelled", "retrying", "average_execution_time"
                    }
                    if expected_keys.issubset(data.keys()):
                        response.success()
                    else:
                        response.failure("Missing required statistics fields")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Unexpected status code: {response.status_code}")
    
    @task(2)
    def health_check(self):
        """Perform health check."""
        with self.client.get("/api/v1/health", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "status" in data and "checks" in data:
                        response.success()
                    else:
                        response.failure("Missing required health fields")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Unexpected status code: {response.status_code}")
    
    @task(1)
    def liveness_probe(self):
        """Test liveness probe (lightweight check)."""
        with self.client.get("/api/v1/health/live", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("status") == "alive":
                        response.success()
                    else:
                        response.failure("Service not alive")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Service not responding: {response.status_code}")
    
    @task(1)
    def admin_stats(self):
        """Get admin statistics."""
        with self.client.get("/api/v1/admin/stats", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    expected_keys = {"jobs", "queue", "cache", "system"}
                    if expected_keys.issubset(data.keys()):
                        response.success()
                    else:
                        response.failure("Missing admin statistics fields")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Unexpected status code: {response.status_code}")


class HighPriorityUser(HttpUser):
    """User that submits high-priority jobs."""
    
    weight = 2  # Less common than regular users
    wait_time = between(2, 5)
    
    def on_start(self):
        """Initialize high-priority user session."""
        self.client.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "LoadTest-Priority/1.0"
        })
    
    @task
    def submit_priority_job(self):
        """Submit high-priority scraping jobs."""
        request_data = {
            "url": random.choice([
                "https://httpbin.org/html",
                "https://httpbin.org/json"
            ]),
            "selector": "h1",
            "options": {
                "extract_text": True,
                "extract_links": True,
                "screenshot": True,
                "timeout": 30
            },
            "priority": random.randint(7, 10),  # High priority
            "metadata": {
                "client": "priority-user",
                "urgency": "high",
                "department": fake.company_suffix()
            }
        }
        
        with self.client.post("/api/v1/scrape", json=request_data, catch_response=True) as response:
            if response.status_code == 202:
                response.success()
            else:
                response.failure(f"Failed to submit priority job: {response.status_code}")


class BulkUser(HttpUser):
    """User that submits multiple jobs in batches."""
    
    weight = 1  # Least common
    wait_time = between(5, 10)
    
    def on_start(self):
        """Initialize bulk user session."""
        self.client.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "LoadTest-Bulk/1.0"
        })
    
    @task
    def submit_bulk_jobs(self):
        """Submit multiple jobs in quick succession."""
        urls = [
            "https://httpbin.org/html",
            "https://httpbin.org/json",
            "https://httpbin.org/status/200",
            "https://httpbin.org/headers",
            "https://httpbin.org/user-agent"
        ]
        
        batch_size = random.randint(3, 7)
        successful_submissions = 0
        
        for i in range(batch_size):
            request_data = {
                "url": random.choice(urls),
                "selector": random.choice(["h1", "p", ".content"]),
                "options": {
                    "extract_text": True,
                    "timeout": 20
                },
                "priority": random.randint(0, 3),  # Lower priority for bulk
                "metadata": {
                    "client": "bulk-user",
                    "batch_id": fake.uuid4(),
                    "batch_position": i + 1,
                    "batch_size": batch_size
                }
            }
            
            response = self.client.post("/api/v1/scrape", json=request_data)
            if response.status_code == 202:
                successful_submissions += 1
        
        # Log batch success rate
        success_rate = successful_submissions / batch_size
        if success_rate >= 0.8:  # 80% success rate threshold
            print(f"Bulk batch successful: {successful_submissions}/{batch_size} jobs submitted")
        else:
            print(f"Bulk batch degraded: {successful_submissions}/{batch_size} jobs submitted")


# Performance test scenarios
class StressTestUser(HttpUser):
    """User for stress testing with aggressive load."""
    
    weight = 0  # Only enabled for stress tests
    wait_time = between(0.1, 0.5)  # Very short wait times
    
    @task(20)
    def rapid_job_submission(self):
        """Submit jobs rapidly for stress testing."""
        request_data = {
            "url": "https://httpbin.org/status/200",
            "options": {
                "extract_text": False,  # Minimal processing
                "timeout": 10
            },
            "priority": 0,
            "metadata": {"test_type": "stress"}
        }
        
        self.client.post("/api/v1/scrape", json=request_data)
    
    @task(5)
    def rapid_status_checks(self):
        """Rapid status checks for stress testing."""
        fake_job_id = fake.uuid4()
        self.client.get(f"/api/v1/scrape/{fake_job_id}")
    
    @task(3)
    def rapid_health_checks(self):
        """Rapid health checks for stress testing."""
        self.client.get("/api/v1/health/live")
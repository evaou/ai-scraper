"""Test configuration and fixtures."""
import asyncio
import os
import tempfile
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Dict, Any
from unittest.mock import Mock, AsyncMock, MagicMock
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from redis import Redis
from faker import Faker

from app.main import app
from app.core.database import Base, get_db
from app.core.redis import get_redis
from app.core.config import Settings
from tests.fixtures.factories import (
    create_scrape_request, create_job, create_completed_job, 
    create_failed_job, create_scraping_result
)

fake = Faker()


# Test settings
@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Override settings for testing."""
    return Settings(
        DATABASE_URL="sqlite+aiosqlite:///test.db",
        REDIS_URL="redis://localhost:6380/15",  # Use test DB
        DEBUG=True,
        LOG_LEVEL="DEBUG",
        API_KEY_REQUIRED=False,
        CACHE_TTL=60,  # Short TTL for tests
        JOB_STATUS_TTL=300,  # Short TTL for tests
    )


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for testing."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    # Use SQLite for fast testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///test.db",
        echo=False,
        future=True
    )
    yield engine
    await engine.dispose()
    # Clean up test database
    try:
        os.unlink("test.db")
    except FileNotFoundError:
        pass


@pytest_asyncio.fixture(scope="session")
async def setup_test_db(test_engine):
    """Set up test database with all tables."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Clean up - drop all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(test_engine, setup_test_db) -> AsyncGenerator[AsyncSession, None]:
    """Get database session for testing with transaction rollback."""
    async with test_engine.begin() as conn:
        async_session = sessionmaker(
            conn, class_=AsyncSession, expire_on_commit=False
        )
        async with async_session() as session:
            yield session
            await session.rollback()


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    mock_redis = MagicMock(spec=Redis)
    mock_redis.ping.return_value = True
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = 1
    mock_redis.flushdb.return_value = True
    mock_redis.exists.return_value = False
    mock_redis.expire.return_value = True
    mock_redis.ttl.return_value = -1
    return mock_redis


@pytest_asyncio.fixture
async def redis_client(mock_redis):
    """Get mocked Redis client for testing."""
    yield mock_redis


@pytest_asyncio.fixture
async def client(db_session, redis_client) -> AsyncGenerator[AsyncClient, None]:
    """Get HTTP client with dependency overrides for testing."""
    
    def override_get_db():
        return db_session
    
    def override_get_redis():
        return redis_client
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    
    async with AsyncClient(app=app, base_url="http://testserver") as ac:
        yield ac
    
    # Clean up overrides
    app.dependency_overrides.clear()


# Sample data fixtures
@pytest.fixture
def sample_scrape_request() -> Dict[str, Any]:
    """Sample scrape request data."""
    return {
        "url": "https://httpbin.org/html",
        "selector": "h1",
        "options": {
            "extract_text": True,
            "extract_links": False,
            "screenshot": False,
            "timeout": 30
        },
        "priority": 0,
        "metadata": {"test": True}
    }


@pytest.fixture
def sample_job_data() -> Dict[str, Any]:
    """Sample job data."""
    return {
        "url": "https://example.com",
        "selector": ".content",
        "options": {
            "screenshot": True,
            "extract_links": True,
            "extract_text": True,
            "timeout": 45
        },
        "priority": 5
    }


@pytest.fixture
def sample_scraping_result() -> Dict[str, Any]:
    """Sample scraping result data."""
    return {
        "content": "Sample page content",
        "html": "<html><body><h1>Test</h1></body></html>",
        "title": "Test Page",
        "links": ["https://example.com/page1", "https://example.com/page2"],
        "images": ["https://example.com/image1.jpg"],
        "meta_description": "Test page description",
        "headings": {"h1": ["Main Title"], "h2": ["Subtitle"]},
        "forms": []
    }


# Mock fixtures for external services
@pytest.fixture
def mock_playwright():
    """Mock Playwright for browser testing."""
    mock_playwright = Mock()
    mock_browser = Mock()
    mock_page = Mock()
    
    # Setup mock chain
    mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
    mock_browser.new_page = AsyncMock(return_value=mock_page)
    mock_page.goto = AsyncMock()
    mock_page.content = AsyncMock(return_value="<html><body>Test</body></html>")
    mock_page.title = AsyncMock(return_value="Test Page")
    mock_page.screenshot = AsyncMock(return_value=b"fake_screenshot")
    mock_page.close = AsyncMock()
    mock_browser.close = AsyncMock()
    
    return mock_playwright


@pytest.fixture
def mock_httpx():
    """Mock httpx client for HTTP requests."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/html"}
    mock_response.text = "<html><body>Test</body></html>"
    mock_response.content = b"<html><body>Test</body></html>"
    mock_response.elapsed.total_seconds.return_value = 1.0
    
    mock_client = Mock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.post = AsyncMock(return_value=mock_response)
    
    return mock_client


# Performance testing fixtures
@pytest.fixture
def benchmark_settings():
    """Settings for benchmark tests."""
    return {
        "min_rounds": 5,
        "max_time": 10.0,
        "warmup": True
    }


# Factory fixtures using our factories
@pytest.fixture
def job_factory():
    """Factory for creating test jobs."""
    return create_job


@pytest.fixture
def completed_job_factory():
    """Factory for creating completed test jobs."""
    return create_completed_job


@pytest.fixture
def failed_job_factory():
    """Factory for creating failed test jobs."""
    return create_failed_job


@pytest.fixture
def scrape_request_factory():
    """Factory for creating scrape requests."""
    return create_scrape_request


@pytest.fixture
def scraping_result_factory():
    """Factory for creating scraping results."""
    return create_scraping_result

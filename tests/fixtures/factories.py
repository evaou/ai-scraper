"""Test factories for generating test data."""

import factory
from datetime import datetime, timedelta
from uuid import uuid4
from faker import Faker

from app.models.job import Job, JobStatus
from app.models.result import Result
from app.models.api_key import ApiKey
from app.schemas.scraping import (
    ScrapeRequest, ScrapingOptions, ScrapingResult, 
    ScrapingMetadata, JobDetailResponse
)

fake = Faker()


class ScrapingOptionsFactory(factory.Factory):
    """Factory for ScrapingOptions."""
    
    class Meta:
        model = ScrapingOptions
    
    wait_for_selector = factory.LazyFunction(lambda: fake.random_element(elements=("h1", ".content", "#main", None)))
    wait_time = factory.LazyFunction(lambda: fake.random_int(min=0, max=10))
    screenshot = factory.LazyFunction(lambda: fake.boolean(chance_of_getting_true=30))
    extract_links = factory.LazyFunction(lambda: fake.boolean(chance_of_getting_true=50))
    extract_images = factory.LazyFunction(lambda: fake.boolean(chance_of_getting_true=30))
    extract_text = True
    user_agent = factory.LazyFunction(lambda: fake.user_agent())
    viewport_width = factory.LazyFunction(lambda: fake.random_element(elements=(1920, 1366, 1440, 1536)))
    viewport_height = factory.LazyFunction(lambda: fake.random_element(elements=(1080, 768, 900, 864)))
    timeout = factory.LazyFunction(lambda: fake.random_int(min=10, max=60))
    follow_redirects = True
    ignore_https_errors = False
    block_resources = factory.LazyFunction(lambda: fake.random_elements(
        elements=("image", "stylesheet", "font", "media"), 
        length=fake.random_int(min=0, max=2),
        unique=True
    ))


class ScrapeRequestFactory(factory.Factory):
    """Factory for ScrapeRequest."""
    
    class Meta:
        model = ScrapeRequest
    
    url = factory.LazyFunction(lambda: fake.url())
    selector = factory.LazyFunction(lambda: fake.random_element(elements=(
        "h1", "p", ".content", "#main", ".article", None
    )))
    options = factory.SubFactory(ScrapingOptionsFactory)
    priority = factory.LazyFunction(lambda: fake.random_int(min=0, max=10))
    scheduled_at = None
    metadata = factory.LazyFunction(lambda: {
        "client": fake.company(),
        "version": fake.numerify("##.##.##"),
        "environment": fake.random_element(elements=("development", "staging", "production"))
    })


class JobFactory(factory.Factory):
    """Factory for Job model."""
    
    class Meta:
        model = Job
    
    id = factory.LazyFunction(uuid4)
    url = factory.LazyFunction(lambda: fake.url())
    selector = factory.LazyFunction(lambda: fake.random_element(elements=(
        "h1", "p", ".content", "#main", ".article", None
    )))
    options = factory.LazyFunction(lambda: {
        "screenshot": fake.boolean(),
        "extract_links": fake.boolean(),
        "extract_text": True,
        "timeout": fake.random_int(min=10, max=60)
    })
    status = JobStatus.PENDING
    created_at = factory.LazyFunction(lambda: fake.date_time_this_month(before_now=True))
    started_at = None
    completed_at = None
    error_message = None
    retry_count = 0
    max_retries = 3
    priority = factory.LazyFunction(lambda: fake.random_int(min=0, max=5))
    scheduled_at = None
    api_key_id = None
    job_metadata = factory.LazyFunction(lambda: {
        "user_agent": fake.user_agent(),
        "ip_address": fake.ipv4(),
        "request_id": fake.uuid4()
    })


class RunningJobFactory(JobFactory):
    """Factory for running job."""
    status = JobStatus.RUNNING
    started_at = factory.LazyFunction(lambda: fake.date_time_this_hour(before_now=True))


class CompletedJobFactory(JobFactory):
    """Factory for completed job."""
    status = JobStatus.COMPLETED
    started_at = factory.LazyFunction(lambda: fake.date_time_this_hour(before_now=True))
    completed_at = factory.LazyFunction(lambda: fake.date_time_this_hour(after_now=False))


class FailedJobFactory(JobFactory):
    """Factory for failed job."""
    status = JobStatus.FAILED
    started_at = factory.LazyFunction(lambda: fake.date_time_this_hour(before_now=True))
    completed_at = factory.LazyFunction(lambda: fake.date_time_this_hour(after_now=False))
    error_message = factory.LazyFunction(lambda: fake.sentence(nb_words=8))
    retry_count = factory.LazyFunction(lambda: fake.random_int(min=1, max=3))


class ScrapingResultFactory(factory.Factory):
    """Factory for ScrapingResult."""
    
    class Meta:
        model = ScrapingResult
    
    content = factory.LazyFunction(lambda: fake.text(max_nb_chars=1000))
    html = factory.LazyFunction(lambda: f"<html><head><title>{fake.sentence()}</title></head><body>{fake.text()}</body></html>")
    links = factory.LazyFunction(lambda: [fake.url() for _ in range(fake.random_int(min=0, max=5))])
    images = factory.LazyFunction(lambda: [fake.image_url() for _ in range(fake.random_int(min=0, max=3))])
    title = factory.LazyFunction(lambda: fake.sentence(nb_words=6))
    meta_description = factory.LazyFunction(lambda: fake.text(max_nb_chars=160))
    headings = factory.LazyFunction(lambda: {
        "h1": [fake.sentence(nb_words=4) for _ in range(fake.random_int(min=0, max=2))],
        "h2": [fake.sentence(nb_words=5) for _ in range(fake.random_int(min=0, max=4))],
        "h3": [fake.sentence(nb_words=3) for _ in range(fake.random_int(min=0, max=6))],
    })
    forms = factory.LazyFunction(lambda: [{
        "action": fake.url(),
        "method": fake.random_element(elements=("GET", "POST")),
        "fields": [fake.word() for _ in range(fake.random_int(min=1, max=5))]
    } for _ in range(fake.random_int(min=0, max=2))])
    screenshot_url = factory.LazyFunction(lambda: fake.image_url() if fake.boolean() else None)


class ScrapingMetadataFactory(factory.Factory):
    """Factory for ScrapingMetadata."""
    
    class Meta:
        model = ScrapingMetadata
    
    execution_time = factory.LazyFunction(lambda: fake.pyfloat(min_value=0.1, max_value=30.0, right_digits=2))
    response_time = factory.LazyFunction(lambda: fake.random_int(min=100, max=5000))
    page_load_time = factory.LazyFunction(lambda: fake.random_int(min=500, max=8000))
    dom_ready_time = factory.LazyFunction(lambda: fake.random_int(min=200, max=3000))
    final_url = factory.LazyFunction(lambda: fake.url())
    status_code = factory.LazyFunction(lambda: fake.random_element(elements=(200, 301, 302, 404, 500)))
    content_type = factory.LazyFunction(lambda: fake.random_element(elements=(
        "text/html", "application/json", "text/plain", "application/xml"
    )))
    content_length = factory.LazyFunction(lambda: fake.random_int(min=1000, max=100000))
    browser_info = factory.LazyFunction(lambda: {
        "name": "chromium",
        "version": fake.numerify("###.#.####.##"),
        "user_agent": fake.user_agent(),
        "viewport": {"width": 1920, "height": 1080}
    })
    timestamp = factory.LazyFunction(lambda: fake.date_time_this_year())


class ResultFactory(factory.Factory):
    """Factory for Result model."""
    
    class Meta:
        model = Result
    
    id = factory.LazyFunction(uuid4)
    job_id = factory.LazyFunction(uuid4)
    data = factory.LazyFunction(lambda: {
        "content": fake.text(),
        "title": fake.sentence(),
        "links": [fake.url() for _ in range(3)],
        "images": [fake.image_url() for _ in range(2)]
    })
    metadata = factory.LazyFunction(lambda: {
        "execution_time": fake.pyfloat(min_value=0.1, max_value=30.0),
        "status_code": 200,
        "browser_info": {"name": "chromium", "version": "120.0.0.0"}
    })
    size_bytes = factory.LazyFunction(lambda: fake.random_int(min=1000, max=100000))
    created_at = factory.LazyFunction(lambda: fake.date_time_this_hour())


class APIKeyFactory(factory.Factory):
    """Factory for ApiKey model."""
    
    class Meta:
        model = ApiKey
    
    id = factory.LazyFunction(uuid4)
    key_hash = factory.LazyFunction(lambda: fake.sha256())
    name = factory.LazyFunction(lambda: f"{fake.word()}-{fake.word()}")
    rate_limit = factory.LazyFunction(lambda: fake.random_int(min=100, max=10000))
    created_at = factory.LazyFunction(lambda: fake.date_time_this_month())
    last_used = factory.LazyFunction(lambda: fake.date_time_this_week())


# Convenience functions for creating test data
def create_scrape_request(**kwargs):
    """Create a ScrapeRequest with optional overrides."""
    return ScrapeRequestFactory(**kwargs)


def create_job(**kwargs):
    """Create a Job with optional overrides."""
    return JobFactory(**kwargs)


def create_running_job(**kwargs):
    """Create a running Job with optional overrides."""
    return RunningJobFactory(**kwargs)


def create_completed_job(**kwargs):
    """Create a completed Job with optional overrides."""
    return CompletedJobFactory(**kwargs)


def create_failed_job(**kwargs):
    """Create a failed Job with optional overrides."""
    return FailedJobFactory(**kwargs)


def create_scraping_result(**kwargs):
    """Create a ScrapingResult with optional overrides."""
    return ScrapingResultFactory(**kwargs)


def create_scraping_metadata(**kwargs):
    """Create ScrapingMetadata with optional overrides."""
    return ScrapingMetadataFactory(**kwargs)
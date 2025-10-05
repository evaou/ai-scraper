"""Playwright scraper worker for processing jobs."""
import asyncio
import logging
import os
import random
import time
from datetime import datetime
from typing import Any
from uuid import UUID

import structlog
from playwright.async_api import Browser, Page, async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal, init_db
from app.core.redis import RedisQueue, cache_job_result, cache_url_result, get_redis
from app.crud.job import job_crud
from app.models.job import Job, JobStatus
from app.models.result import Result

# Configure structured logging for worker
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer() if settings.LOG_FORMAT == "json" else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        logging.getLevelName(settings.LOG_LEVEL.upper())
    ),
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


class ScraperWorker:
    """Playwright-based web scraper worker."""

    def __init__(self):
        self.browser: Browser | None = None
        self.playwright = None
        self.running = False
        self.queue: RedisQueue | None = None

    async def initialize(self):
        """Initialize the worker with browser and database connections."""
        logger.info("Initializing scraper worker")

        try:
            # Initialize database
            await init_db()
            logger.info("Database connection established")

            # Initialize Redis queue
            redis_client = await get_redis()
            self.queue = RedisQueue(redis_client)
            logger.info("Redis queue connection established")

            # Initialize Playwright and browser
            self.playwright = await async_playwright().start()

            # Launch browser with anti-detection settings
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--no-first-run",
                    "--no-zygote",
                    "--disable-gpu",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                ]
            )

            logger.info("Browser launched successfully", browser=settings.PLAYWRIGHT_BROWSER)

        except Exception as e:
            logger.error("Failed to initialize worker", error=str(e))
            raise

    async def shutdown(self):
        """Shutdown the worker gracefully."""
        logger.info("Shutting down scraper worker")

        self.running = False

        try:
            if self.browser:
                await self.browser.close()
                logger.info("Browser closed")

            if self.playwright:
                await self.playwright.stop()
                logger.info("Playwright stopped")

        except Exception as e:
            logger.error("Error during worker shutdown", error=str(e))

    async def run(self):
        """Main worker loop to process scraping jobs."""
        self.running = True
        logger.info("Starting worker main loop")

        while self.running:
            try:
                # Get next job from queue (blocking with timeout)
                job_id = await self.queue.dequeue(timeout=10)

                if job_id:
                    logger.info("Processing job", job_id=job_id)
                    await self.process_job(job_id)

            except TimeoutError:
                # No job available, continue
                continue
            except Exception as e:
                logger.error("Error in worker main loop", error=str(e))
                await asyncio.sleep(5)  # Wait before retrying

        logger.info("Worker main loop stopped")

    async def process_job(self, job_id: str):
        """
        Process a single scraping job.

        Args:
            job_id: UUID of the job to process
        """
        async with AsyncSessionLocal() as db:
            try:
                # Get job from database
                job = await job_crud.get(db, UUID(job_id))
                if not job:
                    logger.error("Job not found", job_id=job_id)
                    await self.queue.complete_job(job_id)
                    return

                # Check if job is already completed or cancelled
                if job.status in [JobStatus.COMPLETED, JobStatus.CANCELLED]:
                    logger.info("Job already completed or cancelled", job_id=job_id, status=job.status)
                    await self.queue.complete_job(job_id)
                    return

                # Update job status to running
                await job_crud.update_status(
                    db,
                    job.id,
                    JobStatus.RUNNING,
                    started_at=datetime.utcnow()
                )

                # Check for cached results first
                cached_result = await self.get_cached_result(job.url)
                if cached_result:
                    logger.info("Using cached result", job_id=job_id, url=job.url)
                    await self.save_result(db, job, cached_result, from_cache=True)
                    await job_crud.update_status(
                        db,
                        job.id,
                        JobStatus.COMPLETED,
                        completed_at=datetime.utcnow()
                    )
                    await self.queue.complete_job(job_id)
                    return

                # Perform scraping
                result_data = await self.scrape_url(job)

                if result_data:
                    # Save result to database
                    await self.save_result(db, job, result_data)

                    # Cache result
                    await cache_url_result(job.url, result_data)
                    await cache_job_result(job_id, result_data)

                    # Update job status to completed
                    await job_crud.update_status(
                        db,
                        job.id,
                        JobStatus.COMPLETED,
                        completed_at=datetime.utcnow()
                    )

                    logger.info("Job completed successfully", job_id=job_id)

                else:
                    # Job failed
                    await job_crud.update_status(
                        db,
                        job.id,
                        JobStatus.FAILED,
                        error_message="Scraping failed - no data extracted",
                        completed_at=datetime.utcnow()
                    )

                    logger.error("Job failed - no data extracted", job_id=job_id)

                await self.queue.complete_job(job_id)

            except Exception as e:
                logger.error("Error processing job", job_id=job_id, error=str(e))

                # Handle job retry logic
                try:
                    job = await job_crud.get(db, UUID(job_id))
                    if job and job.can_retry:
                        await job_crud.increment_retry_count(db, job.id)
                        await self.queue.retry_job(job_id, priority=job.priority)
                        logger.info("Job queued for retry", job_id=job_id, retry_count=job.retry_count + 1)
                    else:
                        await job_crud.update_status(
                            db,
                            UUID(job_id),
                            JobStatus.FAILED,
                            error_message=str(e),
                            completed_at=datetime.utcnow()
                        )
                        await self.queue.complete_job(job_id)
                        logger.error("Job failed permanently", job_id=job_id, error=str(e))

                except Exception as retry_error:
                    logger.error("Error handling job retry", job_id=job_id, error=str(retry_error))
                    await self.queue.complete_job(job_id)

    async def scrape_url(self, job: Job) -> dict[str, Any] | None:
        """
        Scrape a URL using Playwright.

        Args:
            job: Job instance with URL and options

        Returns:
            Dict containing scraped data or None if failed
        """
        if not self.browser:
            logger.error("Browser not initialized")
            return None

        page = None
        try:
            # Create new page with context
            context = await self.browser.new_context(
                viewport={
                    "width": job.options.get("viewport_width", 1920),
                    "height": job.options.get("viewport_height", 1080)
                },
                user_agent=job.options.get("user_agent") or random.choice(settings.USER_AGENTS),
                ignore_https_errors=job.options.get("ignore_https_errors", False),
            )

            page = await context.new_page()

            # Set up resource blocking if specified
            block_resources = job.options.get("block_resources", [])
            if block_resources:
                await page.route("**/*", lambda route: (
                    route.abort() if route.request.resource_type in block_resources else route.continue_()
                ))

            # Navigate to URL with timeout
            timeout = (job.options.get("timeout") or settings.SCRAPE_TIMEOUT) * 1000  # Convert to milliseconds

            start_time = time.time()

            response = await page.goto(
                job.url,
                wait_until="domcontentloaded",
                timeout=timeout
            )

            if not response:
                logger.error("No response received", url=job.url)
                return None

            # Wait for specific selector if provided
            if job.options.get("wait_for_selector"):
                try:
                    await page.wait_for_selector(
                        job.options["wait_for_selector"],
                        timeout=timeout
                    )
                except PlaywrightTimeoutError:
                    logger.warning("Wait for selector timed out", selector=job.options["wait_for_selector"])

            # Additional wait time if specified
            if job.options.get("wait_time"):
                await asyncio.sleep(job.options["wait_time"])

            # Extract data based on selector or get full content
            scraped_data = {}

            # Extract text content
            if job.options.get("extract_text", True):
                if job.selector:
                    try:
                        elements = await page.query_selector_all(job.selector)
                        content_parts = []
                        for element in elements:
                            text = await element.text_content()
                            if text and text.strip():
                                content_parts.append(text.strip())
                        scraped_data["content"] = "\\n".join(content_parts)
                    except Exception as e:
                        logger.warning("Error extracting content with selector", selector=job.selector, error=str(e))
                        # Fallback to body text
                        scraped_data["content"] = await page.locator("body").text_content()
                else:
                    # Extract all text from body
                    scraped_data["content"] = await page.locator("body").text_content()

            # Extract HTML if requested
            if job.options.get("extract_html", False):
                if job.selector:
                    try:
                        element = await page.query_selector(job.selector)
                        if element:
                            scraped_data["html"] = await element.inner_html()
                    except Exception as e:
                        logger.warning("Error extracting HTML with selector", selector=job.selector, error=str(e))
                else:
                    scraped_data["html"] = await page.content()

            # Extract page title
            scraped_data["title"] = await page.title()

            # Extract meta description
            try:
                meta_desc = await page.locator('meta[name="description"]').get_attribute("content")
                scraped_data["meta_description"] = meta_desc
            except:
                scraped_data["meta_description"] = None

            # Extract headings
            if job.options.get("extract_headings", True):
                headings = {}
                for level in range(1, 7):
                    h_elements = await page.query_selector_all(f"h{level}")
                    if h_elements:
                        h_texts = []
                        for elem in h_elements:
                            text = await elem.text_content()
                            if text:
                                h_texts.append(text)
                        headings[f"h{level}"] = h_texts
                scraped_data["headings"] = headings

            # Extract links
            if job.options.get("extract_links", False):
                links = []
                link_elements = await page.query_selector_all("a[href]")
                for element in link_elements:
                    href = await element.get_attribute("href")
                    if href:
                        # Convert relative URLs to absolute
                        if href.startswith("#"):
                            absolute_url = page.url
                        else:
                            absolute_url = await page.evaluate(f'new URL("{href}", "{page.url}").href')
                        if isinstance(absolute_url, str):
                            links.append(absolute_url)

                scraped_data["links"] = list(set(links))  # Remove duplicates

            # Extract images
            if job.options.get("extract_images", False):
                images = []
                img_elements = await page.query_selector_all("img[src]")
                for element in img_elements:
                    src = await element.get_attribute("src")
                    if src:
                        # Convert relative URLs to absolute
                        absolute_url = await page.evaluate(f'new URL("{src}", "{page.url}").href')
                        if isinstance(absolute_url, str):
                            images.append(absolute_url)

                scraped_data["images"] = list(set(images))  # Remove duplicates

            # Extract forms
            if job.options.get("extract_forms", False):
                forms = []
                form_elements = await page.query_selector_all("form")
                for form in form_elements:
                    form_data = {
                        "action": await form.get_attribute("action"),
                        "method": await form.get_attribute("method") or "GET",
                        "inputs": []
                    }

                    input_elements = await form.query_selector_all("input, select, textarea")
                    for input_elem in input_elements:
                        input_data = {
                            "type": await input_elem.get_attribute("type") or "text",
                            "name": await input_elem.get_attribute("name"),
                            "placeholder": await input_elem.get_attribute("placeholder"),
                            "required": await input_elem.get_attribute("required") is not None,
                        }
                        form_data["inputs"].append(input_data)

                    forms.append(form_data)

                scraped_data["forms"] = forms

            # Take screenshot if requested
            if job.options.get("screenshot", False):
                try:
                    screenshot_path = await self.take_screenshot(page, job.id)
                    scraped_data["screenshot_url"] = screenshot_path
                except Exception as e:
                    logger.warning("Failed to take screenshot", error=str(e))

            end_time = time.time()
            execution_time = end_time - start_time

            # Collect metadata
            metadata = {
                "final_url": page.url,
                "status_code": response.status,
                "content_type": response.headers.get("content-type"),
                "response_time": int((end_time - start_time) * 1000),  # milliseconds
                "page_load_time": int(execution_time * 1000),
                "browser_info": {
                    "user_agent": await page.evaluate("navigator.userAgent"),
                    "viewport": page.viewport_size,
                    "browser": settings.PLAYWRIGHT_BROWSER,
                },
                "timestamp": datetime.utcnow().isoformat(),
            }

            logger.info(
                "Scraping completed successfully",
                job_id=str(job.id),
                url=job.url,
                execution_time=execution_time,
                content_length=len(scraped_data.get("content", "")),
                status_code=response.status
            )

            return {
                "data": scraped_data,
                "metadata": metadata,
                "success": True
            }

        except PlaywrightTimeoutError:
            logger.error("Scraping timed out", job_id=str(job.id), url=job.url)
            return None

        except Exception as e:
            logger.error("Error during scraping", job_id=str(job.id), url=job.url, error=str(e))
            return None

        finally:
            if page:
                try:
                    await page.close()
                    await context.close()
                except:
                    pass

    async def take_screenshot(self, page: Page, job_id: UUID) -> str | None:
        """
        Take a screenshot of the page.

        Args:
            page: Playwright page instance
            job_id: Job UUID for filename

        Returns:
            Screenshot file path or None if failed
        """
        try:
            # Create screenshots directory
            screenshot_dir = os.path.join(settings.STORAGE_PATH, "screenshots")
            os.makedirs(screenshot_dir, exist_ok=True)

            # Generate screenshot filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{job_id}_{timestamp}.png"
            filepath = os.path.join(screenshot_dir, filename)

            # Take screenshot
            await page.screenshot(path=filepath, full_page=True)

            return f"/screenshots/{filename}"  # Return relative path for API

        except Exception as e:
            logger.error("Failed to take screenshot", error=str(e))
            return None

    async def get_cached_result(self, url: str) -> dict[str, Any] | None:
        """
        Check if there's a cached result for the URL.

        Args:
            url: URL to check for cached result

        Returns:
            Cached result data or None
        """
        try:
            from app.core.redis import get_cached_url_result
            return await get_cached_url_result(url)
        except Exception as e:
            logger.warning("Error checking cache", url=url, error=str(e))
            return None

    async def save_result(self, db: AsyncSession, job: Job, result_data: dict[str, Any], from_cache: bool = False):
        """
        Save scraping result to database.

        Args:
            db: Database session
            job: Job instance
            result_data: Result data from scraping
            from_cache: Whether result is from cache
        """
        try:
            # Calculate content size
            content = result_data.get("data", {}).get("content", "")
            size_bytes = len(content.encode("utf-8")) if content else 0

            # Create result record
            result = Result(
                job_id=job.id,
                data=result_data.get("data", {}),
                metadata=result_data.get("metadata", {}),
                size_bytes=size_bytes,
                final_url=result_data.get("metadata", {}).get("final_url", job.url),
                status_code=result_data.get("metadata", {}).get("status_code"),
                response_headers=result_data.get("metadata", {}).get("response_headers", {}),
                response_time=result_data.get("metadata", {}).get("response_time"),
                page_load_time=result_data.get("metadata", {}).get("page_load_time"),
                browser_info=result_data.get("metadata", {}).get("browser_info", {}),
                text_content=content[:10000] if content else None,  # Store first 10k chars for search
                links=result_data.get("data", {}).get("links", []),
                screenshot_url=result_data.get("data", {}).get("screenshot_url"),
            )

            db.add(result)
            await db.commit()
            await db.refresh(result)

            logger.info(
                "Result saved successfully",
                job_id=str(job.id),
                result_id=str(result.id),
                from_cache=from_cache,
                size_bytes=size_bytes
            )

        except Exception as e:
            logger.error("Error saving result", job_id=str(job.id), error=str(e))
            await db.rollback()
            raise


async def run_worker():
    """Main function to run the scraper worker."""
    worker = ScraperWorker()

    try:
        await worker.initialize()
        await worker.run()
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error("Worker crashed", error=str(e))
    finally:
        await worker.shutdown()


if __name__ == "__main__":
    asyncio.run(run_worker())

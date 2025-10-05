#!/usr/bin/env python3
"""
Simple USD Selling Spot Rate Scraper

A lightweight scraper to get current USD selling spot rates from Bank of Taiwan.
No email functionality - just pure rate extraction.

Usage:
    python3 usd_rate_simple.py --url "https://rate.bot.com.tw/xrt?Lang=en-US"
    python3 usd_rate_simple.py --url "https://rate.bot.com.tw/xrt?Lang=en-US" --quiet

Author: AI Scraper
Version: 2.0.0 (Simplified)
"""

import argparse
import json
import logging
import os
import re
import time
from decimal import Decimal, InvalidOperation
from typing import Optional, Dict, Any
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from html.parser import HTMLParser
import html


# API Configuration
API_BASE_URL = os.getenv("AI_SCRAPER_API_URL", "http://localhost:8000/api/v1")
SCRAPE_ENDPOINT = f"{API_BASE_URL}/scraping/scrape"
JOB_DETAIL_ENDPOINT = f"{API_BASE_URL}/scraping/scrape"


class ScraperError(Exception):
    """Custom exception for scraper-related errors."""
    pass


class RateExtractionError(Exception):
    """Custom exception for rate extraction errors."""
    pass


def configure_logger(level: int = logging.INFO) -> logging.Logger:
    """
    Configure and return a logger with timestamp formatting.
    
    Args:
        level: Logging level (default: logging.INFO)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(level)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


def submit_job(url: str, css_selector: Optional[str] = None, options: Optional[Dict[str, Any]] = None) -> str:
    """
    Submit a scraping job to the API.
    
    Args:
        url: The URL to scrape
        css_selector: CSS selector for content extraction (optional)
        options: Additional scraping options
        
    Returns:
        Job ID for the submitted job
        
    Raises:
        ScraperError: If the job submission fails
    """
    logger = logging.getLogger(__name__)
    
    payload = {
        "url": url,
        "options": options or {}
    }
    
    if css_selector:
        payload["selector"] = css_selector
    
    logger.info(f"Submitting scraping job for URL: {url}")
    
    try:
        # Convert payload to JSON
        json_data = json.dumps(payload).encode('utf-8')
        
        # Create request
        request = Request(
            SCRAPE_ENDPOINT,
            data=json_data,
            headers={'Content-Type': 'application/json'}
        )
        
        # Make request
        with urlopen(request, timeout=30) as response:
            if response.getcode() != 202:  # API returns 202 for accepted jobs
                raise ScraperError(f"Unexpected status code: {response.getcode()}")
            
            result = json.loads(response.read().decode('utf-8'))
            job_id = result["job_id"]
            
            logger.info(f"Job submitted successfully. Job ID: {job_id}")
            return job_id
        
    except (URLError, HTTPError) as e:
        logger.error(f"Failed to submit job: {e}")
        raise ScraperError(f"Failed to submit scraping job: {e}") from e
    except (KeyError, json.JSONDecodeError) as e:
        logger.error(f"Invalid response format: {e}")
        raise ScraperError(f"Invalid API response: {e}") from e


def poll_job(job_id: str, interval: int = 2, timeout: int = 60) -> Dict[str, Any]:
    """
    Poll the API for job completion.
    
    Args:
        job_id: Job ID to poll
        interval: Polling interval in seconds
        timeout: Maximum time to wait in seconds
        
    Returns:
        Job result payload
        
    Raises:
        ScraperError: If the job fails or times out
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Polling job {job_id} (timeout: {timeout}s, interval: {interval}s)")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            with urlopen(f"{JOB_DETAIL_ENDPOINT}/{job_id}", timeout=10) as response:
                if response.getcode() != 200:
                    raise ScraperError(f"Unexpected status code: {response.getcode()}")
                
                job_data = json.loads(response.read().decode('utf-8'))
                status = job_data.get("status")
                
                logger.debug(f"Job {job_id} status: {status}")
                
                if status == "completed":
                    logger.info(f"Job {job_id} completed successfully")
                    return job_data
                elif status == "failed":
                    error_msg = job_data.get("error_message", "Unknown error")
                    logger.error(f"Job {job_id} failed: {error_msg}")
                    raise ScraperError(f"Job failed: {error_msg}")
                elif status in ["pending", "running"]:
                    logger.debug(f"Job {job_id} still {status}, waiting...")
                    time.sleep(interval)
                else:
                    logger.warning(f"Unknown job status: {status}")
                    time.sleep(interval)
                
        except (URLError, HTTPError, json.JSONDecodeError) as e:
            logger.error(f"Failed to poll job {job_id}: {e}")
            raise ScraperError(f"Failed to poll job: {e}") from e
    
    logger.error(f"Job {job_id} timed out after {timeout} seconds")
    raise ScraperError(f"Job polling timed out after {timeout} seconds")


class SimpleHTMLParser(HTMLParser):
    """Simple HTML parser to extract text content and find elements."""
    
    def __init__(self):
        super().__init__()
        self.text_content = []
        self.current_tag = None
        self.target_classes = []
        self.target_ids = []
        self.found_elements = []
        self.current_element_text = []
        self.inside_target = False
        
    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        attrs_dict = dict(attrs)
        
        # Check if this element matches our CSS selector criteria
        if self.target_classes or self.target_ids:
            if 'class' in attrs_dict and any(cls in attrs_dict['class'] for cls in self.target_classes):
                self.inside_target = True
                self.current_element_text = []
            elif 'id' in attrs_dict and attrs_dict['id'] in self.target_ids:
                self.inside_target = True
                self.current_element_text = []
    
    def handle_endtag(self, tag):
        if self.inside_target:
            self.found_elements.append(''.join(self.current_element_text).strip())
            self.inside_target = False
            self.current_element_text = []
        self.current_tag = None
    
    def handle_data(self, data):
        self.text_content.append(data)
        if self.inside_target:
            self.current_element_text.append(data)
    
    def get_text(self):
        return ' '.join(self.text_content)
    
    def find_by_selector(self, html_content, css_selector):
        """Basic CSS selector parsing - supports class and id selectors."""
        self.reset()
        
        # Parse basic CSS selectors
        if css_selector.startswith('.'):
            # Class selector
            self.target_classes = [css_selector[1:]]
        elif css_selector.startswith('#'):
            # ID selector  
            self.target_ids = [css_selector[1:]]
        else:
            # For more complex selectors, we'll just search in text
            return None
        
        self.feed(html_content)
        return self.found_elements[0] if self.found_elements else None
    
    def reset(self):
        super().reset()
        self.text_content = []
        self.current_tag = None
        self.target_classes = []
        self.target_ids = []
        self.found_elements = []
        self.current_element_text = []
        self.inside_target = False


def extract_usd_selling_rate(html_content: str, css_selector: Optional[str] = None) -> Optional[Decimal]:
    """
    Extract USD selling rate from HTML content.
    
    Args:
        html_content: HTML content to parse
        css_selector: CSS selector to find the rate element
        
    Returns:
        Extracted rate as Decimal, or None if not found
        
    Raises:
        RateExtractionError: If extraction fails
    """
    logger = logging.getLogger(__name__)
    
    try:
        parser = SimpleHTMLParser()
        
        if css_selector:
            # Use specific selector if provided
            element_text = parser.find_by_selector(html_content, css_selector)
            if not element_text:
                logger.warning(f"No elements found with selector: {css_selector}")
                # Fallback to text search
                parser.feed(html_content)
                rate_text = None
            else:
                rate_text = element_text
        
        if not css_selector or not rate_text:
            # Fallback: search for USD selling rate patterns
            logger.info("Searching for USD selling rate patterns in HTML text")
            
            parser.feed(html_content)
            text_content = parser.get_text()
            
            # Bank of Taiwan specific patterns for USD selling rate
            patterns = [
                # Target the SECOND rate (Spot Selling) after finding USD and Spot Buying
                r'American Dollar \(USD\).*?Spot Buying.*?(\d+\.\d+).*?Spot Selling.*?(\d+\.\d+)',
                r'USD.*?data-table="Spot Selling"[^>]*>\s*(\d+\.\d+)',
                # Look for the higher rate in 30.x range (selling rates are typically higher)
                r'\b(3[0-1]\.[4-9]\d{2})\b',  # 30.4xx or 31.4xx format (selling rates are higher)
                r'\b(3[0-1]\.\d{3})\b',  # Fallback: any 30.xxx or 31.xxx format
            ]
            
            for i, pattern in enumerate(patterns):
                matches = re.findall(pattern, text_content, re.IGNORECASE | re.DOTALL)
                if matches:
                    if i == 0:  # First pattern captures both buying and selling - we want selling (second group)
                        rate_text = matches[0][1] if isinstance(matches[0], tuple) and len(matches[0]) >= 2 else matches[0]
                    else:
                        # Handle tuple results from patterns with multiple groups
                        rate_text = matches[0] if isinstance(matches[0], str) else matches[0][-1]
                    logger.debug(f"Pattern {i} matched: {rate_text}")
                    break
            else:
                logger.warning("No USD selling rate patterns found in content")
                return None
        
        # Clean and convert to Decimal
        rate_text = re.sub(r'[^\d.,]', '', str(rate_text))  # Keep only digits, dots, and commas
        rate_text = rate_text.replace(',', '.')  # Normalize decimal separator
        
        if not rate_text:
            logger.warning("No numeric content found in rate text")
            return None
        
        try:
            rate = Decimal(rate_text)
            logger.info(f"Successfully extracted USD selling rate: {rate}")
            return rate
        except InvalidOperation:
            logger.error(f"Invalid numeric format: {rate_text}")
            raise RateExtractionError(f"Invalid rate format: {rate_text}")
            
    except Exception as e:
        logger.error(f"Failed to extract rate from HTML: {e}")
        raise RateExtractionError(f"Rate extraction failed: {e}") from e


def manual_fallback_extraction(url: str, css_selector: Optional[str] = None) -> Optional[Decimal]:
    """
    Manual fallback extraction using direct HTTP request.
    
    Args:
        url: Website URL to scrape
        css_selector: CSS selector (ignored for now)
        
    Returns:
        USD selling rate as Decimal, or None if not found
    """
    logger = logging.getLogger(__name__)
    logger.info("Attempting manual fallback extraction with direct HTTP request")
    
    try:
        # Create request with standard browser headers
        request = Request(url)
        request.add_header('User-Agent', 
                          'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        request.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
        request.add_header('Accept-Language', 'en-US,en;q=0.5')
        request.add_header('Accept-Encoding', 'gzip, deflate')
        request.add_header('DNT', '1')
        request.add_header('Connection', 'keep-alive')
        request.add_header('Upgrade-Insecure-Requests', '1')
        
        # Make request
        with urlopen(request, timeout=30) as response:
            if response.getcode() != 200:
                logger.error(f"HTTP error: {response.getcode()}")
                return None
            
            # Read content
            content = response.read()
            if response.info().get('Content-Encoding') == 'gzip':
                import gzip
                content = gzip.decompress(content)
            
            html_content = content.decode('utf-8', errors='ignore')
            logger.info(f"Successfully fetched {len(html_content)} characters of HTML content")
            
            # Extract rate using the existing function
            rate = extract_usd_selling_rate(html_content, css_selector)
            return rate
            
    except (URLError, HTTPError) as e:
        logger.error(f"Manual fallback failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in manual fallback: {e}")
        return None


def get_usd_selling_rate(url: str, css_selector: Optional[str] = None, **options) -> Optional[Decimal]:
    """
    Get USD selling spot rate from a website.
    
    Args:
        url: Website URL to scrape
        css_selector: CSS selector for the rate element
        **options: Additional options for job submission and polling
        
    Returns:
        USD selling rate as Decimal, or None if not found
        
    Raises:
        ScraperError: If scraping fails
        RateExtractionError: If rate extraction fails
    """
    logger = logging.getLogger(__name__)
    
    # Extract options
    scraping_options = options.get('scraping_options', {})
    poll_interval = options.get('poll_interval', 2)
    poll_timeout = options.get('poll_timeout', 60)
    
    logger.info(f"Starting USD rate extraction from: {url}")
    
    try:
        # Submit scraping job
        job_id = submit_job(url, css_selector, scraping_options)
        
        # Poll for completion
        job_result = poll_job(job_id, poll_interval, poll_timeout)
        
        # Extract content (HTML or text)
        if not job_result.get('data'):
            logger.error("No data in job result")
            raise ScraperError("No data returned from scraping job")
        
        data = job_result['data']
        
        # Check for possible bot detection/blocking
        title = data.get('title', '')
        html_content = data.get('html')
        text_content = data.get('content', '')
        
        if title and not html_content and not text_content:
            logger.warning(f"Website returned title '{title}' but no content - possibly blocked by anti-bot measures")
            logger.info("Suggestion: The website may be using JavaScript to load content or blocking automated requests")
            logger.info("Try: 1) Using wait_time option, 2) Different user agent, 3) Manual verification")
            raise ScraperError(
                f"Content appears to be blocked (title: '{title}' but no HTML/text content). "
                "This website may be using anti-bot detection. Consider using manual fallback."
            )
        
        # Try HTML first, then fallback to content text
        final_content = html_content or text_content
        if not final_content:
            logger.error("No HTML or text content in job result")
            raise ScraperError("No content returned from scraping job")
        
        # Extract rate
        rate = extract_usd_selling_rate(final_content, css_selector)
        
        if rate:
            logger.info(f"Successfully extracted USD selling rate: {rate}")
        else:
            logger.warning("No USD selling rate found")
        
        return rate
        
    except (ScraperError, RateExtractionError) as e:
        logger.error(f"Failed to get USD selling rate: {e}")
        raise


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description="Get USD selling spot rate from Bank of Taiwan"
    )
    parser.add_argument(
        "--url", 
        required=True,
        help="Website URL to scrape"
    )
    parser.add_argument(
        "--selector", 
        help="CSS selector for the rate element"
    )
    parser.add_argument(
        "--timeout", 
        type=int, 
        default=60, 
        help="Polling timeout in seconds (default: 60)"
    )
    parser.add_argument(
        "--interval", 
        type=int, 
        default=2, 
        help="Polling interval in seconds (default: 2)"
    )
    parser.add_argument(
        "--wait-time", 
        type=int, 
        default=0, 
        help="Wait time in seconds after page load (max 30)"
    )
    parser.add_argument(
        "--user-agent", 
        help="Custom User-Agent string for requests"
    )
    parser.add_argument(
        "--screenshot", 
        action="store_true", 
        help="Take a screenshot during scraping"
    )
    parser.add_argument(
        "--manual-fallback", 
        action="store_true", 
        help="Use direct HTTP request as fallback if scraping fails"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true", 
        help="Only output the USD selling rate number"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true", 
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    if args.quiet:
        log_level = logging.CRITICAL  # Suppress all logging in quiet mode
    elif args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    logger = configure_logger(log_level)
    
    try:
        # Build scraping options
        scraping_options = {}
        
        if args.wait_time > 0:
            if args.wait_time > 30:
                logger.warning("Wait time limited to 30 seconds")
                args.wait_time = 30
            scraping_options["wait_time"] = args.wait_time
            
        if args.user_agent:
            scraping_options["user_agent"] = args.user_agent
            
        if args.screenshot:
            scraping_options["screenshot"] = True
            
        # Always extract text to improve success rate
        scraping_options["extract_text"] = True
        
        rate = get_usd_selling_rate(
            url=args.url,
            css_selector=args.selector,
            poll_interval=args.interval,
            poll_timeout=args.timeout,
            scraping_options=scraping_options
        )
        
        if rate:
            if args.quiet:
                print(rate)  # Only print the rate number
            else:
                print(f"💰 USD Selling Rate: {rate} TWD")
        else:
            if not args.quiet:
                print("❌ No USD selling rate found")
            exit(1)
            
    except (ScraperError, RateExtractionError) as e:
        logger.error(f"Error: {e}")
        
        # Try manual fallback if enabled
        if args.manual_fallback:
            logger.info("Attempting manual fallback extraction...")
            try:
                rate = manual_fallback_extraction(args.url, args.selector)
                if rate:
                    if args.quiet:
                        print(rate)  # Only print the rate number
                    else:
                        print(f"💰 USD Selling Rate (manual fallback): {rate} TWD")
                    exit(0)
                else:
                    if not args.quiet:
                        print("❌ Manual fallback also failed to find USD selling rate")
            except Exception as fallback_error:
                logger.error(f"Manual fallback error: {fallback_error}")
        
        exit(1)


if __name__ == "__main__":
    main()
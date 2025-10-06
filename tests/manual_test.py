"""
Manual test script for the ScraperWorker.

This script provides a simple way to test the scraper functionality manually.
"""

import asyncio
import logging
import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.worker.scraper_worker import ScraperWorker
from app.schemas.scraping import ScrapeRequest


# Configure logging for better visibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)


async def test_basic_scraping():
    """Test basic web scraping functionality."""
    print("🚀 Starting ScraperWorker test...")
    
    async with ScraperWorker() as worker:
        # Test 1: Basic HTML page (example.com)
        print("\n📄 Test 1: Basic HTML scraping")
        request = ScrapeRequest(url="https://example.com")
        
        response = await worker.scrape(request)
        
        if response.error:
            print(f"❌ Error: {response.error}")
        else:
            print(f"✅ Success: Retrieved {len(response.html)} characters")
            print(f"⏱️  Execution time: {response.metadata['execution_time']:.2f}s")
            print(f"🌐 Browser: {response.metadata['browser_info']['name']}")
            
            # Check if expected content is present
            if "<h1>Example Domain</h1>" in response.html:
                print("✅ Found expected h1 content")
            else:
                print("❌ Expected h1 content not found")
        
        print(f"🔍 Response metadata: {response.metadata}")
        
        # Test 2: JavaScript-heavy page (with timeout)
        print("\n🔄 Test 2: JavaScript rendering test")
        request = ScrapeRequest(
            url="https://quotes.toscrape.com/js/",
            wait_for_selector=".quote",
            timeout=15
        )
        
        response = await worker.scrape(request)
        
        if response.error:
            print(f"❌ Error: {response.error}")
        else:
            print(f"✅ Success: Retrieved {len(response.html)} characters")
            print(f"⏱️  Execution time: {response.metadata['execution_time']:.2f}s")
            
            # Count quotes found
            quote_count = response.html.count('class="quote"')
            print(f"📝 Found {quote_count} quotes on page")
        
        # Test 3: Test with custom headers
        print("\n🔧 Test 3: Custom headers test")
        request = ScrapeRequest(
            url="https://httpbin.org/headers",
            headers={"X-Test-Header": "ScraperWorker-Test"}
        )
        
        response = await worker.scrape(request)
        
        if response.error:
            print(f"❌ Error: {response.error}")
        else:
            print(f"✅ Success: Retrieved {len(response.html)} characters")
            if "X-Test-Header" in response.html:
                print("✅ Custom header was sent successfully")
            else:
                print("❌ Custom header not found in response")


async def test_error_handling():
    """Test error handling and retry logic."""
    print("\n🛡️  Testing error handling and retry logic...")
    
    async with ScraperWorker() as worker:
        # Test 1: Invalid URL
        print("\n❌ Test: Invalid URL")
        request = ScrapeRequest(url="https://this-domain-does-not-exist-12345.com")
        
        response = await worker.scrape(request)
        
        if response.error:
            print(f"✅ Expected error caught: {response.error}")
        else:
            print(f"❌ Unexpected success for invalid URL")
        
        # Test 2: Timeout test
        print("\n⏰ Test: Timeout handling")
        request = ScrapeRequest(
            url="https://httpbin.org/delay/35",  # 35 second delay
            timeout=5  # 5 second timeout
        )
        
        response = await worker.scrape(request)
        
        if response.error and "timeout" in response.error.lower():
            print(f"✅ Timeout handled correctly: {response.error}")
        else:
            print(f"❌ Timeout not handled as expected")


async def main():
    """Run all tests."""
    print("🕷️  Scraper Worker Manual Test Suite")
    print("=" * 50)
    
    try:
        await test_basic_scraping()
        await test_error_handling()
        
        print("\n" + "=" * 50)
        print("✅ All tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
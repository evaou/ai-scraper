# USD Selling Spot Rate Scraper

This script uses the web scraping API to extract USD selling spot rates from financial websites.

## Features

- Submits scraping jobs to the API and polls for completion
- Extracts USD rates using CSS selectors or pattern matching
- Handles various rate formats (with commas, different decimal separators)
- Uses standard Python libraries only (no external dependencies)
- Provides detailed logging and error handling
- Built-in test functionality

## Prerequisites

1. Make sure the web scraping API is running:
   ```bash
   docker compose up -d
   ```

2. Verify the API is healthy:
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

## Usage

### Basic Usage

```bash
# Test the scraper with a demo site
python3 usd_rate_scraper.py --test

# Scrape from a website with CSS selector
python3 usd_rate_scraper.py --url "https://example-bank.com/rates" --selector ".usd-sell-rate"

# Scrape with automatic pattern detection (no selector)
python3 usd_rate_scraper.py --url "https://example-bank.com/rates"
```

### Advanced Options

```bash
# Verbose logging
python3 usd_rate_scraper.py --url "https://example.com" --verbose

# Custom timeout and polling interval
python3 usd_rate_scraper.py --url "https://example.com" --timeout 120 --interval 5
```

## CSS Selectors

The script supports basic CSS selectors:

- **Class selectors**: `.rate-value`, `.usd-sell`
- **ID selectors**: `#usd-rate`, `#selling-rate`

Examples of common selectors for financial sites:
- `.currency-rate`
- `#usd-sell`
- `.sell-rate`
- `.exchange-rate`

## Pattern Matching

When no CSS selector is provided, the script searches for common patterns:

1. `USD.*?sell.*?(\\d+[\\.,]\\d+)` - "USD selling rate: 1.25"
2. `sell.*?USD.*?(\\d+[\\.,]\\d+)` - "Selling USD: 1.25"
3. `USD.*?(\\d+[\\.,]\\d+)` - "USD 1.25"
4. `selling.*?(\\d+[\\.,]\\d+)` - "Selling rate: 1.25"
5. `\\$\\s*(\\d+[\\.,]\\d+)` - "$ 1.25"
6. `(\\d+[\\.,]\\d+).*USD` - "1.25 USD"

## Examples with Real Financial Sites

### Example 1: Generic Bank Website

```bash
# If the bank displays rates like: <div class="sell-rate">1.2345</div>
python3 usd_rate_scraper.py --url "https://bank.example.com/exchange-rates" --selector ".sell-rate"
```

### Example 2: Currency Exchange Site

```bash
# If the site displays: <span id="usd-selling">1.2345</span>
python3 usd_rate_scraper.py --url "https://exchange.example.com/rates" --selector "#usd-selling"
```

### Example 3: Automatic Detection

```bash
# Let the script find USD rates automatically
python3 usd_rate_scraper.py --url "https://finance.example.com/currencies"
```

## Output

Successful execution will output:
```
💰 USD Selling Rate: 1.2345
```

## Error Handling

The script handles various error conditions:

- **Network errors**: Connection timeouts, HTTP errors
- **API errors**: Job failures, invalid responses
- **Parsing errors**: Invalid HTML, missing rate data
- **Rate format errors**: Non-numeric values, invalid formats

## Programmatic Usage

You can also import and use the functions programmatically:

```python
from usd_rate_scraper import get_usd_selling_rate, configure_logger

# Set up logging
logger = configure_logger()

try:
    # Get USD rate with CSS selector
    rate = get_usd_selling_rate(
        url="https://bank.example.com/rates",
        css_selector=".usd-sell",
        poll_timeout=60
    )
    
    if rate:
        print(f"Current USD selling rate: {rate}")
    else:
        print("No rate found")
        
except Exception as e:
    print(f"Error: {e}")
```

## Testing

Run the built-in test to verify everything is working:

```bash
python3 usd_rate_scraper.py --test
```

This will scrape a demo site and verify the API is functioning correctly.

## Troubleshooting

### API Not Available
```
Error: Failed to submit scraping job: [Errno 61] Connection refused
```
**Solution**: Make sure the Docker services are running with `docker compose up -d`

### No Rate Found
```
❌ No USD selling rate found
```
**Solutions**:
1. Try a different CSS selector
2. Use automatic pattern matching (remove `--selector`)
3. Check the website manually to verify the rate format
4. Use `--verbose` to see detailed logs

### Job Timeout
```
Error: Job polling timed out after 60 seconds
```
**Solutions**:
1. Increase timeout with `--timeout 120`
2. Check if the target website is responding slowly
3. Verify the website is accessible

## Supported Rate Formats

The script can extract rates in various formats:
- `1.2345` (decimal)
- `1,2345` (comma as decimal separator)
- `1.234,56` (European format)
- `$1.23` (with currency symbol)
- `1.23 USD` (with currency code)

All formats are normalized to Decimal for precision.
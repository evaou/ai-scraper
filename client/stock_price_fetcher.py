#!/usr/bin/env python3
"""
Stock Price Fetcher from Google Sheets

A script to fetch and parse stock prices from Google Sheets via AI Scraper API.
Requires a running AI Scraper API server for HTML parsing and data processing.

Usage:
    python3 stock_price_fetcher.py --url "https://docs.google.com/spreadsheets/..." --api-server "https://paramita-scraper.duckdns.org/api/v1"
    python3 stock_price_fetcher.py --config config.json

Author: AI Scraper
Version: 1.0.0
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse, urljoin
import csv
from io import StringIO




# Default Configuration
DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSkBKRRPFnMC85TZbONYkjBU10sJplY1SjJo31SbnnjcX9YfkafVRY5q2x4nLXeh5JYxMyBlUEqkIgs/pubhtml"
API_BASE_URL = os.getenv("AI_SCRAPER_API_URL", "http://paramita-scraper.duckdns.org/api/v1")
SCRAPE_ENDPOINT = f"{API_BASE_URL}/scrape"


class StockFetcherError(Exception):
    """Custom exception for stock fetcher-related errors."""
    pass


class DataParsingError(Exception):
    """Custom exception for data parsing errors."""
    pass


def configure_logger(level: int = logging.INFO) -> logging.Logger:
    """
    Configure and return a logger with timestamp formatting.
    
    Args:
        level: Logging level (default: INFO)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(level)
    
    # Avoid duplicate handlers if logger already exists
    if logger.handlers:
        return logger
    
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


def fetch_stock_data_via_api(url: str, api_server: str, timeout: int = 30) -> List[Dict[str, Any]]:
    """
    Fetch and parse stock data from Google Sheets HTML using AI Scraper API.
    
    Args:
        url: Google Sheets pubhtml URL
        api_server: AI Scraper API server base URL
        timeout: Request timeout in seconds
    
    Returns:
        List of parsed stock dictionaries
    
    Raises:
        StockFetcherError: If API call or parsing fails
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Ensure we're using the pubhtml URL for API parsing
        if 'pub?output=csv' in url:
            url = url.replace('pub?output=csv', 'pubhtml')
        elif '/pub' in url and 'pubhtml' not in url:
            url = url.replace('/pub', '/pubhtml')
        
        logger.info(f"Parsing stock data via API from: {url}")
        
        # Prepare API payload (simple pattern like USD scraper)
        payload = {
            'url': url
        }
        
        # Convert to JSON
        json_payload = json.dumps(payload).encode('utf-8')
        
        # Prepare API request
        api_endpoint = urljoin(api_server.rstrip('/') + '/', 'scrape')
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'StockPriceFetcher/1.0.0',
            'Accept': 'application/json'
        }
        
        # Add API key if available
        api_key = os.getenv('AI_SCRAPER_API_KEY')
        if api_key:
            headers['X-API-Key'] = api_key
        
        logger.info(f"Sending scraping request to API: {api_endpoint}")
        
        request = Request(api_endpoint, data=json_payload, headers=headers, method='POST')
        
        with urlopen(request, timeout=timeout) as response:
            if response.getcode() not in [200, 201]:
                raise StockFetcherError(f"API returned HTTP {response.getcode()}")
            
            api_response = json.loads(response.read().decode('utf-8'))
            
            # Extract stock data from API response
            stocks = extract_stocks_from_api_response(api_response)
            logger.info(f"Successfully parsed {len(stocks)} stocks via API")
            return stocks
            
    except json.JSONDecodeError as e:
        raise StockFetcherError(f"Invalid JSON response from API: {e}")
    except (URLError, HTTPError) as e:
        raise StockFetcherError(f"API server error: {e}")
    except Exception as e:
        raise StockFetcherError(f"Unexpected API error: {e}")


def extract_stocks_from_api_response(api_response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract stock data from AI Scraper API response.
    
    Args:
        api_response: API response containing scraped data
    
    Returns:
        List of stock dictionaries
    
    Raises:
        DataParsingError: If extraction fails
    """
    logger = logging.getLogger(__name__)
    
    try:
        stocks = []
        
        # Check if we have scraped content
        if 'content' not in api_response:
            raise DataParsingError("No content in API response")
        
        content = api_response['content']
        
        # Process scraped content - expect HTML or text content
        raw_data = content if isinstance(content, str) else (content.get('text', '') or content.get('html', '') or str(content))
        
        if raw_data:
            # Parse HTML content for stock data  
            stocks = parse_raw_stock_data(raw_data)
        else:
            raise DataParsingError("No usable content found in API response")
        
        # Add metadata to each stock
        for stock in stocks:
            stock['source'] = 'ai_scraper_api'
            stock['fetched_at'] = datetime.utcnow().isoformat() + 'Z'
        
        logger.info(f"Extracted {len(stocks)} stocks from API response")
        return stocks
        
    except Exception as e:
        raise DataParsingError(f"Failed to extract stocks from API response: {e}")


def parse_table_data(table: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parse stock data from table structure.
    
    Args:
        table: Table data from API response
    
    Returns:
        List of stock dictionaries
    """
    logger = logging.getLogger(__name__)
    stocks = []
    
    try:
        rows = table.get('rows', [])
        if not rows:
            return stocks
        
        # Assume first row is header
        headers = [str(cell).strip().lower() for cell in rows[0]]
        
        # Map column indices
        symbol_idx = None
        price_idx = None
        name_idx = None
        change_idx = None
        
        for i, header in enumerate(headers):
            if any(keyword in header for keyword in ['symbol', 'ticker', 'code']):
                symbol_idx = i
            elif any(keyword in header for keyword in ['price', 'close', 'current', 'last']):
                price_idx = i
            elif any(keyword in header for keyword in ['name', 'company', 'title']):
                name_idx = i
            elif any(keyword in header for keyword in ['change', 'diff']):
                change_idx = i
        
        # Process data rows
        for row_num, row in enumerate(rows[1:], start=2):
            try:
                if len(row) < max(filter(None, [symbol_idx, price_idx])):
                    continue
                
                stock_data = {}
                
                # Extract symbol
                if symbol_idx is not None:
                    symbol = str(row[symbol_idx]).strip().upper()
                    if symbol:
                        stock_data['symbol'] = symbol
                    else:
                        continue
                else:
                    stock_data['symbol'] = f"STOCK_{row_num}"
                
                # Extract price
                if price_idx is not None:
                    price_str = str(row[price_idx]).strip()
                    price_clean = price_str.replace('$', '').replace(',', '').replace('%', '')
                    try:
                        price = float(price_clean) if price_clean else 0.0
                        stock_data['price'] = price
                    except ValueError:
                        stock_data['price'] = 0.0
                else:
                    stock_data['price'] = 0.0
                
                # Extract optional fields
                if name_idx is not None and name_idx < len(row):
                    stock_data['name'] = str(row[name_idx]).strip()
                else:
                    stock_data['name'] = stock_data['symbol']
                
                if change_idx is not None and change_idx < len(row):
                    change_str = str(row[change_idx]).strip()
                    change_clean = change_str.replace('$', '').replace(',', '').replace('%', '')
                    try:
                        stock_data['change'] = float(change_clean) if change_clean else 0.0
                    except ValueError:
                        stock_data['change'] = 0.0
                
                stocks.append(stock_data)
                
            except Exception as e:
                logger.warning(f"Row {row_num}: Error parsing stock data - {e}")
                continue
        
        return stocks
        
    except Exception as e:
        logger.warning(f"Error parsing table data: {e}")
        return []


def parse_raw_stock_data(raw_data: str) -> List[Dict[str, Any]]:
    """
    Parse stock data from raw HTML/text when no structured tables are found.
    
    Args:
        raw_data: Raw HTML or text content
    
    Returns:
        List of stock dictionaries
    """
    logger = logging.getLogger(__name__)
    stocks = []
    
    try:
        # This is a fallback parser - implement basic pattern matching
        # for common stock data formats in HTML tables
        
        # Look for table-like patterns in the text
        lines = raw_data.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Try to match stock symbol and price patterns
            # This is a simple heuristic - can be enhanced
            parts = line.split()
            if len(parts) >= 2:
                # Look for symbol-like patterns (letters, possibly with dots)
                potential_symbol = parts[0].upper()
                if potential_symbol.replace('.', '').isalpha() and len(potential_symbol) <= 5:
                    # Look for price-like patterns
                    for part in parts[1:]:
                        price_str = part.replace('$', '').replace(',', '')
                        try:
                            price = float(price_str)
                            if 0 < price < 10000:  # Reasonable price range
                                stock_data = {
                                    'symbol': potential_symbol,
                                    'price': price,
                                    'name': potential_symbol,
                                    'change': 0.0
                                }
                                stocks.append(stock_data)
                                break
                        except ValueError:
                            continue
        
        logger.info(f"Parsed {len(stocks)} stocks from raw data")
        return stocks
        
    except Exception as e:
        logger.warning(f"Error parsing raw stock data: {e}")
        return []


def fetch_csv_data_fallback(url: str, timeout: int = 30) -> str:
    """
    Fallback method to fetch CSV data directly when API is not available.
    
    Args:
        url: Google Sheets CSV export URL
        timeout: Request timeout in seconds
    
    Returns:
        Raw CSV content as string
    
    Raises:
        StockFetcherError: If fetch fails
    """
    import urllib.request
    from urllib.request import HTTPRedirectHandler, build_opener
    
    logger = logging.getLogger(__name__)
    
    try:
        # Convert to CSV format if needed
        if 'pubhtml' in url:
            url = url.replace('pubhtml', 'pub?output=csv')
        elif 'pub?output=csv' not in url and '/pub' not in url:
            separator = '&' if '?' in url else '?'
            url = f"{url}{separator}output=csv"
        
        logger.info(f"Fetching CSV fallback from: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Create opener that handles redirects
        opener = build_opener(HTTPRedirectHandler)
        request = Request(url, headers=headers)
        
        with opener.open(request, timeout=timeout) as response:
            if response.getcode() != 200:
                raise StockFetcherError(f"HTTP {response.getcode()}: Failed to fetch data")
            
            csv_content = response.read().decode('utf-8')
            
            if not csv_content.strip():
                raise StockFetcherError("Empty CSV content received")
            
            logger.info(f"Successfully fetched {len(csv_content)} bytes of CSV data")
            return csv_content
            
    except (URLError, HTTPError) as e:
        raise StockFetcherError(f"Network error fetching CSV: {e}")
    except UnicodeDecodeError as e:
        raise StockFetcherError(f"Failed to decode CSV content: {e}")
    except Exception as e:
        raise StockFetcherError(f"Unexpected error fetching CSV: {e}")


def parse_csv_data(csv_content: str) -> List[Dict[str, Any]]:
    """
    Parse CSV content into structured stock data.
    
    Args:
        csv_content: Raw CSV content string
    
    Returns:
        List of stock dictionaries with normalized keys
    
    Raises:
        DataParsingError: If parsing fails
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Parse CSV
        csv_file = StringIO(csv_content)
        reader = csv.DictReader(csv_file)
        
        # Get field names and normalize them
        if not reader.fieldnames:
            raise DataParsingError("No column headers found in CSV")
        
        # Map common column name variations
        column_mapping = {}
        for field in reader.fieldnames:
            field_lower = field.lower().strip()
            if any(keyword in field_lower for keyword in ['symbol', 'ticker', 'code']):
                column_mapping['symbol'] = field
            elif 'low price' in field_lower or 'low_price' in field_lower:
                column_mapping['low_price'] = field
            elif any(keyword in field_lower for keyword in ['current price', 'current_price', 'price', 'close', 'current', 'last']):
                column_mapping['current_price'] = field
            elif any(keyword in field_lower for keyword in ['name', 'company', 'title']):
                column_mapping['name'] = field
            elif any(keyword in field_lower for keyword in ['change', 'diff']):
                column_mapping['change'] = field
            elif any(keyword in field_lower for keyword in ['volume', 'vol']):
                column_mapping['volume'] = field
        
        logger.info(f"Column mapping detected: {column_mapping}")
        
        stocks = []
        for row_num, row in enumerate(reader, start=2):
            try:
                stock_data = {}
                
                # Extract symbol (required)
                if 'symbol' in column_mapping:
                    symbol = str(row[column_mapping['symbol']]).strip().upper()
                    if symbol:
                        stock_data['symbol'] = symbol
                    else:
                        logger.warning(f"Row {row_num}: Empty symbol, skipping")
                        continue
                else:
                    logger.warning(f"Row {row_num}: No symbol column found, using row number")
                    stock_data['symbol'] = f"STOCK_{row_num}"
                
                # Extract current price (required)
                current_price = 0.0
                if 'current_price' in column_mapping:
                    price_str = str(row[column_mapping['current_price']]).strip()
                    price_clean = price_str.replace('$', '').replace(',', '').replace('%', '')
                    try:
                        current_price = float(price_clean) if price_clean else 0.0
                    except ValueError:
                        logger.warning(f"Row {row_num}: Invalid current price '{price_str}', using 0.0")
                elif 'low_price' in column_mapping:  # Fallback if no current price column
                    logger.info(f"Row {row_num}: Using low_price as current price (fallback)")
                    price_str = str(row[column_mapping['low_price']]).strip()
                    price_clean = price_str.replace('$', '').replace(',', '').replace('%', '')
                    try:
                        current_price = float(price_clean) if price_clean else 0.0
                    except ValueError:
                        logger.warning(f"Row {row_num}: Invalid price '{price_str}', using 0.0")
                
                stock_data['price'] = current_price
                
                # Extract low price threshold
                low_price = 0.0
                if 'low_price' in column_mapping:
                    low_price_str = str(row[column_mapping['low_price']]).strip()
                    low_price_clean = low_price_str.replace('$', '').replace(',', '').replace('%', '')
                    try:
                        low_price = float(low_price_clean) if low_price_clean else 0.0
                    except ValueError:
                        logger.warning(f"Row {row_num}: Invalid low price '{low_price_str}', using 0.0")
                
                stock_data['low_price'] = low_price
                
                # Determine if this is a buy opportunity (current price <= low price)
                stock_data['is_buy_opportunity'] = current_price > 0 and low_price > 0 and current_price <= low_price
                
                # Extract optional fields
                if 'name' in column_mapping:
                    stock_data['name'] = str(row[column_mapping['name']]).strip()
                else:
                    stock_data['name'] = stock_data['symbol']
                
                if 'change' in column_mapping:
                    change_str = str(row[column_mapping['change']]).strip()
                    change_clean = change_str.replace('$', '').replace(',', '').replace('%', '')
                    try:
                        stock_data['change'] = float(change_clean) if change_clean else 0.0
                    except ValueError:
                        stock_data['change'] = 0.0
                
                if 'volume' in column_mapping:
                    volume_str = str(row[column_mapping['volume']]).strip()
                    volume_clean = volume_str.replace(',', '')
                    try:
                        stock_data['volume'] = int(float(volume_clean)) if volume_clean else 0
                    except ValueError:
                        stock_data['volume'] = 0
                
                # Add metadata
                stock_data['source'] = 'google_sheets'
                stock_data['fetched_at'] = datetime.utcnow().isoformat() + 'Z'
                
                stocks.append(stock_data)
                
            except Exception as e:
                logger.warning(f"Row {row_num}: Error parsing stock data - {e}")
                continue
        
        logger.info(f"Successfully parsed {len(stocks)} stocks from CSV")
        return stocks
        
    except Exception as e:
        raise DataParsingError(f"Failed to parse CSV data: {e}")


def call_api_server(stocks_data: List[Dict[str, Any]], api_url: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Send stock data to remote API server for enhanced processing.
    
    Args:
        stocks_data: List of stock dictionaries
        api_url: API server base URL
        timeout: Request timeout in seconds
    
    Returns:
        API response with processed stock data
    
    Raises:
        StockFetcherError: If API call fails
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Prepare API payload
        payload = {
            'stocks': stocks_data,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'source': 'stock_price_fetcher',
            'version': '1.0.0'
        }
        
        # Convert to JSON
        json_payload = json.dumps(payload).encode('utf-8')
        
        # Prepare request
        api_endpoint = urljoin(api_url.rstrip('/') + '/', 'scraping/process-stocks')
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'StockPriceFetcher/1.0.0',
            'Accept': 'application/json'
        }
        
        logger.info(f"Sending {len(stocks_data)} stocks to API: {api_endpoint}")
        
        request = Request(api_endpoint, data=json_payload, headers=headers, method='POST')
        
        with urlopen(request, timeout=timeout) as response:
            if response.getcode() not in [200, 201]:
                raise StockFetcherError(f"API returned HTTP {response.getcode()}")
            
            response_data = json.loads(response.read().decode('utf-8'))
            logger.info("Successfully processed stocks via API server")
            return response_data
            
    except json.JSONDecodeError as e:
        raise StockFetcherError(f"Invalid JSON response from API: {e}")
    except (URLError, HTTPError) as e:
        raise StockFetcherError(f"API server error: {e}")
    except Exception as e:
        raise StockFetcherError(f"Unexpected API error: {e}")


def check_thresholds(stocks: List[Dict[str, Any]], thresholds: Dict[str, float]) -> List[Dict[str, Any]]:
    """
    Check which stocks are at or below buy thresholds.
    
    Args:
        stocks: List of stock dictionaries
        thresholds: Dictionary mapping symbol to threshold price
    
    Returns:
        List of stocks that meet buy criteria
    """
    logger = logging.getLogger(__name__)
    buy_opportunities = []
    
    for stock in stocks:
        symbol = stock.get('symbol', '').upper()
        price = stock.get('price', 0)
        
        if symbol in thresholds:
            threshold = thresholds[symbol]
            if price <= threshold and price > 0:  # Exclude zero prices
                discount_pct = ((threshold - price) / threshold) * 100
                buy_opportunity = {
                    **stock,
                    'threshold': threshold,
                    'discount_pct': round(discount_pct, 2),
                    'buy_signal': True
                }
                buy_opportunities.append(buy_opportunity)
                logger.info(f"🎯 Buy signal: {symbol} at ${price:.2f} (target: ${threshold:.2f}, {discount_pct:.1f}% discount)")
            else:
                logger.info(f"📈 No signal: {symbol} at ${price:.2f} (target: ${threshold:.2f})")
    
    return buy_opportunities


def load_config_file(config_path: str) -> Dict[str, Any]:
    """Load configuration from JSON file."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise StockFetcherError(f"Failed to load config file '{config_path}': {e}")


def main():
    """Main function to fetch and process stock prices."""
    parser = argparse.ArgumentParser(
        description="Fetch stock prices from Google Sheets CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch via AI Scraper API (default)
  python3 stock_price_fetcher.py
  
  # Fetch from custom HTML URL via API
  python3 stock_price_fetcher.py --url "https://docs.google.com/spreadsheets/.../pubhtml"
  
  # Fallback to CSV parsing (no API)
  python3 stock_price_fetcher.py --no-api
  
  # Check specific symbols with thresholds via API
  python3 stock_price_fetcher.py --symbols AAPL,GOOGL --thresholds 150.0,2800.0
  
  # Load configuration from file
  python3 stock_price_fetcher.py --config config.json
        """
    )
    
    parser.add_argument(
        '--url',
        default=DEFAULT_SHEET_URL,
        help='Google Sheets CSV export URL (default: built-in URL)'
    )
    
    parser.add_argument(
        '--api-server',
        help='AI Scraper API server base URL for HTML parsing (recommended)'
    )
    
    parser.add_argument(
        '--symbols',
        help='Comma-separated list of stock symbols to monitor'
    )
    
    parser.add_argument(
        '--thresholds',
        help='Comma-separated list of threshold prices (must match symbols order)'
    )
    
    parser.add_argument(
        '--config',
        help='JSON configuration file path'
    )
    
    parser.add_argument(
        '--output',
        choices=['table'],
        default='table',
        help='Output format (table format only)'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress informational output'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.WARNING if args.quiet else logging.DEBUG if args.debug else logging.INFO
    logger = configure_logger(log_level)
    
    try:
        # Load configuration from file if specified
        config = {}
        if args.config:
            config = load_config_file(args.config)
            # Override with command line args
            if args.url != DEFAULT_SHEET_URL:
                config['url'] = args.url
            if args.api_server:
                config['api_server'] = args.api_server
            if args.symbols:
                config['symbols'] = args.symbols.split(',')
            if args.thresholds:
                config['thresholds'] = [float(t) for t in args.thresholds.split(',')]
        else:
            # Use command line args
            config = {
                'url': args.url,
                'api_server': args.api_server,
                'symbols': args.symbols.split(',') if args.symbols else [],
                'thresholds': [float(t) for t in args.thresholds.split(',')] if args.thresholds else []
            }
        
        # Validate symbols and thresholds match
        if config.get('symbols') and config.get('thresholds'):
            if len(config['symbols']) != len(config['thresholds']):
                raise StockFetcherError("Number of symbols must match number of thresholds")
        
        # Fetch stock data
        logger.info("Starting stock price fetch process...")
        
        # Check if API server is available for HTML parsing
        api_server = config.get('api_server')
        if api_server:
            try:
                # Try API approach first (no health check, direct call like USD scraper)
                stocks = fetch_stock_data_via_api(config['url'], api_server)
                logger.info("Successfully fetched stock data via AI Scraper API")
                
            except (URLError, HTTPError, StockFetcherError) as e:
                logger.warning(f"API server not available ({e}), falling back to CSV parsing")
                logger.info("To use API parsing, ensure the AI Scraper server is running")
                # Fallback to CSV parsing
                csv_content = fetch_csv_data_fallback(config['url'])
                stocks = parse_csv_data(csv_content)
        else:
            # Use CSV parsing when no API server specified
            logger.info("No API server specified, using direct CSV parsing")
            csv_content = fetch_csv_data_fallback(config['url'])
            stocks = parse_csv_data(csv_content)
        
        # Note: API processing is now integrated into the fetch process above
        
        # Extract buy opportunities from spreadsheet data
        buy_opportunities = [stock for stock in stocks if stock.get('is_buy_opportunity', False)]
        
        # Add discount calculation for buy opportunities
        for opp in buy_opportunities:
            current_price = opp.get('price', 0)
            low_price = opp.get('low_price', 0)
            if low_price > 0:
                discount_pct = ((low_price - current_price) / low_price) * 100
                opp['discount_pct'] = max(0, discount_pct)  # Ensure non-negative
                opp['threshold'] = low_price  # For compatibility with existing output format
        
        # Prepare output
        result = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'total_stocks': len(stocks),
            'stocks': stocks,
            'buy_opportunities': buy_opportunities,
            'buy_count': len(buy_opportunities),
            'source_url': config['url'],
            'api_processed': bool(config.get('api_server'))
        }
        
        # Output all stocks when any buy opportunities exist, otherwise just buy opportunities
        if buy_opportunities:
            # Show all stocks with buy opportunities highlighted
            print(f"{'Symbol':<10} {'Current':<10} {'LowPrice':<10} {'Status':<10} {'Savings':<10}")
            print("-" * 52)
            
            # Create a set of buy opportunity symbols for quick lookup
            buy_symbols = {stock.get('symbol', '') for stock in buy_opportunities}
            
            for stock in stocks:
                symbol = stock.get('symbol', '')[:9]
                current = f"${stock.get('price', 0):.2f}"
                low_price = f"${stock.get('low_price', 0):.2f}"
                
                if symbol in buy_symbols:
                    status = "🎯 BUY"
                    # Calculate discount for buy opportunities
                    current_price = stock.get('price', 0)
                    low_price_val = stock.get('low_price', 0)
                    if low_price_val > 0:
                        discount_pct = ((low_price_val - current_price) / low_price_val) * 100
                        discount = f"{max(0, discount_pct):.1f}%"
                    else:
                        discount = "0.0%"
                else:
                    status = "HOLD"
                    discount = "-"
                
                print(f"{symbol:<10} {current:<10} {low_price:<10} {status:<10} {discount:<10}")
        else:
            # Always print this message as it's the main output, even in quiet mode
            print("No buy opportunities found. All stocks are above their low price thresholds.")
        
        logger.info(f"Successfully processed {len(stocks)} stocks")
        if buy_opportunities:
            logger.info(f"Found {len(buy_opportunities)} buy opportunities")
        
    except (StockFetcherError, DataParsingError) as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
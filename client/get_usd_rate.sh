#!/bin/bash

# Simple USD Rate Getter
# Gets current USD selling spot rate from Bank of Taiwan

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRAPER_SCRIPT="$SCRIPT_DIR/usd_rate_scraper.py"
URL="https://rate.bot.com.tw/xrt?Lang=en-US"

# Check if Python script exists
if [ ! -f "$SCRAPER_SCRIPT" ]; then
    echo "Error: USD Rate Scraper not found at: $SCRAPER_SCRIPT" >&2
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed" >&2
    exit 1
fi

# Get the rate (quietly, errors suppressed)
if RATE=$(python3 "$SCRAPER_SCRIPT" --url "$URL" --manual-fallback --quiet 2>/dev/null); then
    echo "$RATE"
    exit 0
else
    echo "Error: Failed to get USD rate" >&2
    exit 1
fi
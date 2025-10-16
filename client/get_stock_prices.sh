#!/usr/bin/env bash

###############################################################################
# get_stock_prices.sh
#
# Production-aware Stock Price Fetcher helper.
#
# Fetches stock data via the deployed AI Scraper API using HTML parsing
# for enhanced data extraction.
#
# Usage:
#   ./get_stock_prices.sh                              # Production API (defaults to deployed API)
#   ./get_stock_prices.sh --prod                       # Use production API URL
#   ./get_stock_prices.sh --api http://paramita-scraper.duckdns.org/api/v1
#   ./get_stock_prices.sh --config stock_config.json --quiet
#   AI_SCRAPER_API_URL=... ./get_stock_prices.sh
#
# Exit Codes:
#   0  Success (data printed)
#   1  Generic failure  
#   2  Prerequisite missing
###############################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/stock_price_fetcher.py"

# Default target URL for Google Sheets
DEFAULT_SHEET_URL="https://docs.google.com/spreadsheets/d/e/2PACX-1vSkBKRRPFnMC85TZbONYkjBU10sJplY1SjJo31SbnnjcX9YfkafVRY5q2x4nLXeh5JYxMyBlUEqkIgs/pubhtml"

# Defaults (can be overridden)
: "${AI_SCRAPER_API_URL:=http://paramita-scraper.duckdns.org/api/v1}"
PROD_API_URL_DEFAULT="http://paramita-scraper.duckdns.org/api/v1"
USE_PROD=false
CUSTOM_API=""
QUIET=false

print_usage() {
    sed -n '1,30p' "$0" | grep -E '^# ' | sed 's/^# //'
}

log() { $QUIET && return 0; echo "[get_stock_prices] $*" >&2; }
err() { echo "[get_stock_prices][error] $*" >&2; }



# Initialize variables with defaults first
url="${STOCK_SHEET_URL:-$DEFAULT_SHEET_URL}"
config_file=""
output_format="table"
quiet=false
debug=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --prod)
            USE_PROD=true
            shift
            ;;
        --api)
            CUSTOM_API="$2"; shift 2;
            ;;
        --url)
            url="$2"; shift 2;
            ;;
        --config)
            config_file="$2"; shift 2;
            ;;
        --output)
            output_format="$2"; shift 2;
            ;;
        --quiet|-q)
            QUIET=true; quiet=true; shift;
            ;;
        --debug)
            debug=true; shift;
            ;;
        --help|-h)
            print_usage; exit 0;
            ;;
        *)
            err "Unknown argument: $1"; print_usage; exit 1;
            ;;
    esac
done

# Resolve API base url precedence: explicit flag > prod shortcut > existing env
if [[ -n "$CUSTOM_API" ]]; then
    AI_SCRAPER_API_URL="$CUSTOM_API"
elif $USE_PROD; then
    AI_SCRAPER_API_URL="$PROD_API_URL_DEFAULT"
fi

# Validate python & script
if [[ ! -f "$PYTHON_SCRIPT" ]]; then
    err "Stock price fetcher script not found at $PYTHON_SCRIPT"; exit 2;
fi
if ! command -v python3 >/dev/null 2>&1; then
    err "python3 is required"; exit 2;
fi

log "Target URL: $url"
log "API Base: $AI_SCRAPER_API_URL (will attempt API mode first)"

export AI_SCRAPER_API_URL

# Build Python command arguments
python_args=()

if [[ -n "$config_file" ]]; then
    python_args+=("--config" "$config_file")
else
    python_args+=("--url" "$url")
fi

python_args+=("--output" "$output_format")

# Always try API mode first by passing the API server
python_args+=("--api-server" "$AI_SCRAPER_API_URL")

if [[ "$quiet" == true ]]; then
    python_args+=("--quiet")
fi

if [[ "$debug" == true ]]; then
    python_args+=("--debug")
fi

RESULT=""
API_FAILED=false

# 1. Try API-powered fetch (HTML parsing via AI Scraper API)
# Capture both output and stderr to determine actual mode used
TEMP_LOG=$(mktemp)
if RESULT=$(python3 "$PYTHON_SCRIPT" "${python_args[@]}" 2>"$TEMP_LOG"); then
    # Check stderr output to determine if API actually worked or fell back to CSV
    if grep -q "falling back to CSV parsing" "$TEMP_LOG"; then
        log "API mode failed; retrieved stock data via CSV fallback"
        API_FAILED=true
    elif grep -q "Successfully fetched stock data via AI Scraper API" "$TEMP_LOG"; then
        log "Retrieved stock data via AI Scraper API"
    else
        log "Retrieved stock data successfully"
    fi
else
    API_FAILED=true
    log "API mode failed; attempting CSV fallback..."
fi
rm -f "$TEMP_LOG"

# 2. Fallback to CSV mode if needed (remove --api-server argument)
if [[ -z "${RESULT}" ]]; then
    # Remove API server from args for fallback
    python_args_fallback=()
    skip_next=false
    for arg in "${python_args[@]}"; do
        if [[ "$skip_next" == true ]]; then
            skip_next=false
            continue
        fi
        if [[ "$arg" == "--api-server" ]]; then
            skip_next=true
            continue
        fi
        python_args_fallback+=("$arg")
    done
    
    if RESULT=$(python3 "$PYTHON_SCRIPT" "${python_args_fallback[@]}" 2>/dev/null); then
        log "Retrieved stock data via CSV fallback"
    fi
fi

if [[ -n "${RESULT}" ]]; then
    echo "$RESULT"
    exit 0
fi

if $API_FAILED; then
    err "Failed to retrieve stock data (API + CSV fallback)"
else
    err "Failed to retrieve stock data"
fi
exit 1
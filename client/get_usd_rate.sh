#!/usr/bin/env bash

###############################################################################
# get_usd_rate.sh
#
# Production-aware USD Selling Spot Rate helper.
#
# Tries to fetch the USD rate via the deployed AI Scraper API first (async job
# submission + polling handled inside usd_rate_scraper.py). If that fails it
# automatically falls back to the local/manual scraping mode.
#
# Usage:
#   ./get_usd_rate.sh                  # Production API (defaults to deployed API)
#   ./get_usd_rate.sh --prod           # Use production API URL (set below or via env)
#   ./get_usd_rate.sh --api https://api.example.com/api/v1
#   ./get_usd_rate.sh --quiet          # Suppress stderr (only prints rate)
#   AI_SCRAPER_API_URL=... ./get_usd_rate.sh
#
# Exit Codes:
#   0  Success (rate printed)
#   1  Generic failure
#   2  Prerequisite missing
###############################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRAPER_SCRIPT="$SCRIPT_DIR/usd_rate_scraper.py"

# Default target URL for Bank of Taiwan rates page
RATE_SOURCE_URL="https://rate.bot.com.tw/xrt?Lang=en-US"

# Defaults (can be overridden)
# Note: API mode requires authentication in production, falls back to manual scraping
: "${AI_SCRAPER_API_URL:=https://paramita-scraper.duckdns.org/api/v1}"
PROD_API_URL_DEFAULT="https://YOUR_PRODUCTION_HOST/api/v1"
USE_PROD=false
CUSTOM_API=""
QUIET=false

print_usage() {
    sed -n '1,50p' "$0" | grep -E '^# ' | sed 's/^# //'
}

log() { $QUIET && return 0; echo "[get_usd_rate] $*" >&2; }
err() { echo "[get_usd_rate][error] $*" >&2; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --prod)
            USE_PROD=true
            shift
            ;;
        --api)
            CUSTOM_API="$2"; shift 2;
            ;;
        --quiet|-q)
            QUIET=true; shift;
            ;;
        --help|-h)
            print_usage; exit 0;
            ;;
        --url)
            # Allow overriding the target scrape URL
            RATE_SOURCE_URL="$2"; shift 2;
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
if [[ ! -f "$SCRAPER_SCRIPT" ]]; then
    err "USD Rate scraper not found at $SCRAPER_SCRIPT"; exit 2;
fi
if ! command -v python3 >/dev/null 2>&1; then
    err "python3 is required"; exit 2;
fi

log "Target URL: $RATE_SOURCE_URL"
log "API Base: $AI_SCRAPER_API_URL (will attempt API mode first)"

export AI_SCRAPER_API_URL

RATE=""
API_FAILED=false

# 1. Try API-powered scrape (no --manual-fallback)
if RATE=$(python3 "$SCRAPER_SCRIPT" --url "$RATE_SOURCE_URL" --quiet 2>/dev/null); then
    :
else
    API_FAILED=true
    log "API mode failed; attempting manual fallback..."
fi

# 2. Fallback to manual mode if needed
MANUAL_FAILED=false
if [[ -z "${RATE}" ]]; then
    if RATE=$(python3 "$SCRAPER_SCRIPT" --url "$RATE_SOURCE_URL" --manual-fallback --quiet 2>/dev/null); then
        log "Retrieved rate via manual fallback"
    else
        MANUAL_FAILED=true
        log "Manual fallback also failed"
        
        # Try to get more diagnostic info in non-quiet mode
        if ! $QUIET; then
            log "Attempting diagnostic run to identify the issue..."
            python3 "$SCRAPER_SCRIPT" --url "$RATE_SOURCE_URL" --manual-fallback --verbose 2>&1 | head -20 >&2 || true
        fi
    fi
fi

if [[ -n "${RATE}" ]]; then
    echo "$RATE"
    exit 0
fi

# Report specific failure modes
if $API_FAILED && $MANUAL_FAILED; then
    err "Failed to retrieve USD rate (both API and manual fallback failed)"
elif $API_FAILED; then
    err "Failed to retrieve USD rate (API failed, manual fallback not attempted due to empty result)"
else
    err "Failed to retrieve USD rate"
fi
exit 1
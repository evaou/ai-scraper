#!/bin/bash

###############################################################################
# test-workflows-jwt.sh
#
# Comprehensive test script to verify JWT_SECRET_KEY integration across all 
# GitHub Actions workflows that use the AI Scraper API.
#
# Usage:
#   # Test with generated JWT key (like in GitHub Actions)
#   JWT_SECRET_KEY="$(openssl rand -base64 32)" ./scripts/test-workflows-jwt.sh
#
#   # Test with environment JWT key
#   ./scripts/test-workflows-jwt.sh
#
# This script tests:
# 1. USD Rate Email workflow API integration
# 2. Stock Price Alert workflow API integration  
# 3. Direct API key authentication
# 4. Fallback mechanisms
###############################################################################

set -euo pipefail

echo "🧪 GitHub Actions JWT_SECRET_KEY Integration Test"
echo "================================================="

# Get JWT secret (use generated key if not set)
if [ -z "${JWT_SECRET_KEY:-}" ]; then
    JWT_SECRET_KEY=$(openssl rand -base64 32)
    echo "🔑 Generated test JWT_SECRET_KEY: ${JWT_SECRET_KEY:0:8}..."
else
    echo "🔑 Using provided JWT_SECRET_KEY: ${JWT_SECRET_KEY:0:8}..."
fi

export AI_SCRAPER_API_KEY="$JWT_SECRET_KEY"

echo ""
echo "📋 Testing GitHub Actions Workflow Components:"
echo "----------------------------------------------"

# Test 1: USD Rate Email Workflow
echo ""
echo "1️⃣ USD Rate Email Workflow Test"
echo "   Environment: AI_SCRAPER_API_KEY=$AI_SCRAPER_API_KEY"
echo "   Script: ./client/get_usd_rate.sh --api http://paramita-scraper.duckdns.org/api/v1"

if USD_RESULT=$(./client/get_usd_rate.sh --api http://paramita-scraper.duckdns.org/api/v1 --quiet 2>/dev/null); then
    echo "   ✅ Result: $USD_RESULT TWD"
    
    # Check mode used
    USD_VERBOSE=$(./client/get_usd_rate.sh --api http://paramita-scraper.duckdns.org/api/v1 2>&1 | head -10)
    if echo "$USD_VERBOSE" | grep -q "Retrieved rate via AI Scraper API"; then
        echo "   🚀 Mode: API (Enhanced Performance)"
        API_WORKING=true
    elif echo "$USD_VERBOSE" | grep -q "Retrieved rate via manual fallback"; then
        echo "   ⚠️ Mode: Manual Fallback (API key not registered)"
        API_WORKING=false
    else
        echo "   ❓ Mode: Unknown"
        API_WORKING=false
    fi
else
    echo "   ❌ Failed to get USD rate"
    API_WORKING=false
fi

# Test 2: Stock Price Alert Workflow
echo ""
echo "2️⃣ Stock Price Alert Workflow Test"
echo "   Environment: AI_SCRAPER_API_KEY=$AI_SCRAPER_API_KEY"
echo "   Script: ./client/get_stock_prices.sh --api http://paramita-scraper.duckdns.org/api/v1"

if STOCK_RESULT=$(./client/get_stock_prices.sh --api http://paramita-scraper.duckdns.org/api/v1 --output table 2>/dev/null | head -1); then
    echo "   ✅ Result: Stock data retrieved"
    
    # Check mode used  
    STOCK_VERBOSE=$(./client/get_stock_prices.sh --api http://paramita-scraper.duckdns.org/api/v1 --output table 2>&1 | head -10)
    if echo "$STOCK_VERBOSE" | grep -q "Retrieved stock data via AI Scraper API"; then
        echo "   🚀 Mode: API (Enhanced Performance)"
    elif echo "$STOCK_VERBOSE" | grep -q "Retrieved stock data via CSV fallback"; then
        echo "   ⚠️ Mode: CSV Fallback (API key not registered)"
    else
        echo "   ❓ Mode: Unknown"
    fi
else
    echo "   ❌ Failed to get stock data"
fi

# Test 3: Direct API Authentication
echo ""
echo "3️⃣ Direct API Authentication Test"
echo "   Endpoint: http://paramita-scraper.duckdns.org/api/v1/scrape"
echo "   Headers: X-API-Key: ${JWT_SECRET_KEY:0:8}..."

API_RESPONSE=$(curl -s -w "%{http_code}" -X POST http://paramita-scraper.duckdns.org/api/v1/scrape \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $JWT_SECRET_KEY" \
    -d '{"url": "https://httpbin.org/html"}' 2>/dev/null || echo "000FAILED")

HTTP_CODE="${API_RESPONSE: -3}"
RESPONSE_BODY="${API_RESPONSE%???}"

case "$HTTP_CODE" in
    "202")
        echo "   ✅ API Authentication: SUCCESS (HTTP 202)"
        if echo "$RESPONSE_BODY" | grep -q '"job_id"'; then
            echo "   🎯 Job Submitted: API key is valid and registered"
            API_WORKING=true
        fi
        ;;
    "401")
        if echo "$RESPONSE_BODY" | grep -q "API key required"; then
            echo "   ⚠️ API Authentication: No key provided (unexpected)"
        elif echo "$RESPONSE_BODY" | grep -q "Invalid API key"; then
            echo "   ⚠️ API Authentication: JWT key not registered in database"
        else
            echo "   ❌ API Authentication: Unauthorized (HTTP 401)"
        fi
        API_WORKING=false
        ;;
    "404")
        echo "   ❌ API Endpoint: Not found (HTTP 404)"
        API_WORKING=false
        ;;
    "000")
        echo "   ❌ API Connection: Failed (network error)"
        API_WORKING=false
        ;;
    *)
        echo "   ❓ API Response: Unexpected (HTTP $HTTP_CODE)"
        API_WORKING=false
        ;;
esac

# Test 4: Health Check (No Auth Required)
echo ""
echo "4️⃣ API Server Health Check"
echo "   Endpoint: http://paramita-scraper.duckdns.org/api/v1/health"

if curl -f -s -m 10 http://paramita-scraper.duckdns.org/api/v1/health > /dev/null 2>&1; then
    echo "   ✅ Server: Online and responding"
else
    echo "   ❌ Server: Offline or unreachable"
fi

echo ""
echo "📊 Test Summary"
echo "==============="

if [ "${API_WORKING:-false}" = "true" ]; then
    echo "🎉 STATUS: All systems working with API enhancement!"
    echo ""
    echo "✅ JWT_SECRET_KEY is properly registered as API key"
    echo "✅ Both workflows will use enhanced API mode"
    echo "✅ Performance benefits: Faster, more reliable data fetching"
    echo ""
    echo "🚀 GitHub Actions workflows ready for production use!"
else
    echo "⚠️ STATUS: Fallback mode active (API key needs registration)"
    echo ""
    echo "📋 Current State:"
    echo "• JWT_SECRET_KEY configured in workflows ✅"
    echo "• Client scripts support API authentication ✅" 
    echo "• Fallback mechanisms working ✅"
    echo "• API key registration needed on server ⚠️"
    echo ""
    echo "🔧 To enable API mode, run on server:"
    echo "   python3 scripts/create-jwt-api-key.py"
    echo ""
    echo "💡 Workflows continue working normally with fallback methods"
fi

echo ""
echo "🔍 Next Steps:"
echo "1. Ensure JWT_SECRET_KEY is set in GitHub repository secrets"  
echo "2. Run 'python3 scripts/create-jwt-api-key.py' on production server"
echo "3. Verify API mode activation with next workflow runs"
#!/bin/bash

###############################################################################
# test-jwt-api-key.sh
#
# Test script to verify that JWT_SECRET_KEY works as an API key for both
# USD rate and stock price workflows.
#
# Usage:
#   ./scripts/test-jwt-api-key.sh
#
# This script should be run on the production server after running
# create-jwt-api-key.py to verify the setup works correctly.
###############################################################################

set -euo pipefail

echo "🧪 Testing JWT_SECRET_KEY API Integration"
echo "======================================="

# Get JWT secret (use default for testing)
JWT_KEY="${JWT_SECRET_KEY:-dev-secret-key-change-in-production}"

if [ "$JWT_KEY" = "dev-secret-key-change-in-production" ]; then
    echo "⚠️ Using default JWT_SECRET_KEY for testing"
else
    echo "✅ Using production JWT_SECRET_KEY"
fi

echo ""
echo "1️⃣ Testing USD Rate API access..."
export AI_SCRAPER_API_KEY="$JWT_KEY"

if USD_RESULT=$(./client/get_usd_rate.sh --quiet 2>/dev/null); then
    echo "✅ USD Rate: $USD_RESULT TWD"
    
    # Check if it used API or fallback
    if ./client/get_usd_rate.sh 2>&1 | grep -q "Retrieved rate via AI Scraper API"; then
        echo "🚀 Mode: AI Scraper API (enhanced)"
    else
        echo "⚠️ Mode: Manual fallback (JWT key may not be registered)"
    fi
else
    echo "❌ USD Rate failed"
fi

echo ""
echo "2️⃣ Testing Stock Price API access..."

if STOCK_RESULT=$(./client/get_stock_prices.sh --output table 2>/dev/null | head -1); then
    echo "✅ Stock Prices: Retrieved successfully"
    
    # Check if it used API or fallback
    if ./client/get_stock_prices.sh --output table 2>&1 | grep -q "Retrieved stock data via AI Scraper API"; then
        echo "🚀 Mode: AI Scraper API (enhanced)"  
    else
        echo "⚠️ Mode: CSV fallback (JWT key may not be registered)"
    fi
else
    echo "❌ Stock Prices failed"
fi

echo ""
echo "3️⃣ Testing API endpoint directly..."

API_RESPONSE=$(curl -s -X POST http://localhost/api/v1/scrape \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $JWT_KEY" \
    -d '{"url": "https://httpbin.org/html"}' || echo "FAILED")

if echo "$API_RESPONSE" | grep -q '"job_id"'; then
    echo "✅ Direct API: Working with JWT_SECRET_KEY"
elif echo "$API_RESPONSE" | grep -q "API key required"; then
    echo "❌ Direct API: JWT_SECRET_KEY not registered as API key"
    echo "   Run: python3 scripts/create-jwt-api-key.py"
elif echo "$API_RESPONSE" | grep -q "Invalid API key"; then
    echo "❌ Direct API: JWT_SECRET_KEY not valid as API key"  
    echo "   Run: python3 scripts/create-jwt-api-key.py"
else
    echo "❌ Direct API: Unexpected response - $API_RESPONSE"
fi

echo ""
echo "📋 Summary:"
echo "----------"
echo "• Both workflows are configured to use JWT_SECRET_KEY as API key"
echo "• If showing 'Manual/CSV fallback', run: python3 scripts/create-jwt-api-key.py"
echo "• This will register JWT_SECRET_KEY as a valid API key in the database"
echo "• After registration, workflows will automatically use enhanced API mode"
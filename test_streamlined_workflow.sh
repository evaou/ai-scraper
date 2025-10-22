#!/bin/bash

# Test the streamlined USD rate workflow logic

echo "=== Streamlined USD Rate Workflow Test ==="
echo

# Test 1: Enhanced API mode (with API key)
echo "Test 1: Enhanced API mode with API key"
export AI_SCRAPER_API_KEY="dbf0f924ee130437f06e4e98acec95e390a55a1456be9de9cf0c7aaf91f4cfaa"
export AI_SCRAPER_API_URL="http://paramita-scraper.duckdns.org/api/v1"

# Simulate workflow logic
RATE=""

if [ -n "$AI_SCRAPER_API_KEY" ]; then
    echo "🚀 Trying enhanced API mode with smart anti-detection..."
    RATE=$(./client/get_usd_rate.sh --api "$AI_SCRAPER_API_URL" --enhanced --quiet 2>/dev/null || true)
    
    if echo "$RATE" | grep -qE '^[0-9]+\.[0-9]+$'; then
        echo "✅ Enhanced API mode successful: $RATE"
        API_MODE="enhanced_smart"
    else
        RATE=""
        echo "⚠️ Enhanced API mode failed, trying manual fallback..."
    fi
fi

if [ -z "$RATE" ]; then
    echo "🔄 Using manual fallback mode..."
    RATE=$(./client/get_usd_rate.sh --quiet 2>/dev/null || true)
    
    if echo "$RATE" | grep -qE '^[0-9]+\.[0-9]+$'; then
        echo "✅ Manual fallback successful: $RATE"
        API_MODE="manual_fallback"
    else
        RATE=""
        echo "❌ Manual fallback also failed"
        API_MODE="failed"
    fi
fi

echo "📊 Final Result: Rate=$RATE, Mode=$API_MODE"
echo

# Test 2: Manual-only mode (no API key)
echo "Test 2: Manual-only mode (no API key)"
unset AI_SCRAPER_API_KEY
RATE2=""

if [ -z "$AI_SCRAPER_API_KEY" ]; then
    echo "⚠️ JWT_SECRET_KEY not configured - using manual fallback only"
    API_MODE2="no_key"
    
    echo "🔄 Using manual fallback mode..."
    RATE2=$(./client/get_usd_rate.sh --quiet 2>/dev/null || true)
    
    if echo "$RATE2" | grep -qE '^[0-9]+\.[0-9]+$'; then
        echo "✅ Manual fallback successful: $RATE2"
        API_MODE2="manual_only"
    else
        RATE2=""
        echo "❌ Manual fallback failed"
        API_MODE2="failed"
    fi
fi

echo "📊 Final Result: Rate=$RATE2, Mode=$API_MODE2"
echo

# Summary
echo "=== Streamlined Workflow Summary ==="
echo "✅ Enhanced API attempt: ${RATE:+SUCCESS ($RATE)}${RATE:-FAILED}"
echo "✅ Manual fallback test: ${RATE2:+SUCCESS ($RATE2)}${RATE2:-FAILED}"
echo
echo "🎯 Workflow Benefits:"
echo "   - Cleaner logs (removed debug noise)"
echo "   - Faster execution (no retries, direct fallback)"
echo "   - Clear mode reporting (enhanced_smart, manual_fallback, etc.)"
echo "   - Simplified logic (try enhanced → fallback to manual)"

echo
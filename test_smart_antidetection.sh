#!/bin/bash

# Test smart anti-detection features for USD rate collection

echo "=== Smart Anti-Detection USD Rate Test ==="
echo

# Test 1: Standard API mode (without enhancement)
echo "Test 1: Standard API mode (likely to be blocked)"
export AI_SCRAPER_API_KEY="dbf0f924ee130437f06e4e98acec95e390a55a1456be9de9cf0c7aaf91f4cfaa"
export AI_SCRAPER_API_URL="http://paramita-scraper.duckdns.org/api/v1"

echo "⏱️  Testing standard API mode (timeout: 30s)..."
timeout 30s ./client/get_usd_rate.sh --api "$AI_SCRAPER_API_URL" --quiet 2>/dev/null
STANDARD_EXIT=$?
if [ $STANDARD_EXIT -eq 0 ]; then
    echo "✅ Standard API mode succeeded (unexpected but good!)"
elif [ $STANDARD_EXIT -eq 124 ]; then
    echo "⏰ Standard API mode timed out (expected - likely blocked)"
else
    echo "❌ Standard API mode failed (exit code: $STANDARD_EXIT) - likely blocked"
fi

echo

# Test 2: Enhanced anti-detection mode
echo "Test 2: Enhanced anti-detection mode"
echo "⏱️  Testing enhanced API mode with smart anti-detection (timeout: 45s)..."
echo "🛡️  Features: Stealth mode, human simulation, advanced headers, viewport simulation"

timeout 45s ./client/get_usd_rate.sh --api "$AI_SCRAPER_API_URL" --enhanced --quiet 2>/dev/null
ENHANCED_EXIT=$?
if [ $ENHANCED_EXIT -eq 0 ]; then
    echo "🎉 Enhanced anti-detection mode succeeded!"
    ENHANCED_RATE=$(timeout 45s ./client/get_usd_rate.sh --api "$AI_SCRAPER_API_URL" --enhanced --quiet 2>/dev/null)
    echo "📊 Retrieved rate: $ENHANCED_RATE TWD"
elif [ $ENHANCED_EXIT -eq 124 ]; then
    echo "⏰ Enhanced mode timed out (may need longer wait times)"
else
    echo "⚠️  Enhanced mode failed (exit code: $ENHANCED_EXIT) - falling back to manual"
fi

echo

# Test 3: Manual fallback (should always work)
echo "Test 3: Manual fallback mode (direct HTTP)"
MANUAL_RATE=$(./client/get_usd_rate.sh --quiet 2>/dev/null)
MANUAL_EXIT=$?
if [ $MANUAL_EXIT -eq 0 ] && [ -n "$MANUAL_RATE" ]; then
    echo "✅ Manual fallback succeeded: $MANUAL_RATE TWD"
else
    echo "❌ Manual fallback failed (exit code: $MANUAL_EXIT)"
fi

echo

# Test 4: Compare rate consistency
echo "Test 4: Rate consistency check"
if [ -n "${ENHANCED_RATE:-}" ] && [ -n "${MANUAL_RATE:-}" ]; then
    if [ "$ENHANCED_RATE" = "$MANUAL_RATE" ]; then
        echo "✅ Rates match perfectly: Enhanced($ENHANCED_RATE) = Manual($MANUAL_RATE)"
    else
        echo "⚠️  Rate difference: Enhanced($ENHANCED_RATE) vs Manual($MANUAL_RATE)"
        # Calculate difference
        DIFF=$(echo "$ENHANCED_RATE - $MANUAL_RATE" | bc -l 2>/dev/null || echo "Cannot calculate")
        echo "   Difference: $DIFF TWD"
    fi
else
    echo "⚠️  Cannot compare - one or both rates unavailable"
fi

echo

# Summary
echo "=== Anti-Detection Test Summary ==="
if [ $ENHANCED_EXIT -eq 0 ]; then
    echo "🎯 SUCCESS: Smart anti-detection bypassed website blocking!"
    echo "🚀 Recommendation: Use enhanced mode in production workflow"
elif [ $MANUAL_EXIT -eq 0 ]; then
    echo "⚙️  PARTIAL SUCCESS: Manual fallback works, enhanced mode needs tuning"
    echo "🔧 Recommendation: Enhanced mode as primary, manual as reliable fallback"
else
    echo "❌ FAILURE: Both enhanced and manual modes failed"
    echo "🔍 Recommendation: Check network connectivity and website status"
fi

echo
echo "💡 Enhanced mode features tested:"
echo "   - Stealth browser fingerprinting"
echo "   - Human behavior simulation"  
echo "   - Advanced security headers"
echo "   - Viewport and user agent simulation"
echo "   - Resource blocking for performance"
echo "   - Extended timeout handling"

echo
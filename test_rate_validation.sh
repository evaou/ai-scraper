#!/bin/bash

# Test rate validation logic

echo "=== Testing Rate Validation Logic ==="

# Test 1: Valid rate
RATE="30.895"
if echo "$RATE" | grep -qE '^[0-9]+\.[0-9]+$'; then
    echo "✅ Test 1 PASS: '$RATE' is valid"
else
    echo "❌ Test 1 FAIL: '$RATE' should be valid"
fi

# Test 2: Error message (should fail validation)
RATE="[get_usd_rate][error] Failed to retrieve USD rate"
if echo "$RATE" | grep -qE '^[0-9]+\.[0-9]+$'; then
    echo "❌ Test 2 FAIL: '$RATE' should not be valid"
else
    echo "✅ Test 2 PASS: '$RATE' correctly identified as invalid"
fi

# Test 3: Empty rate
RATE=""
if echo "$RATE" | grep -qE '^[0-9]+\.[0-9]+$'; then
    echo "❌ Test 3 FAIL: Empty rate should not be valid"
else
    echo "✅ Test 3 PASS: Empty rate correctly identified as invalid"
fi

# Test 4: bc comparison with valid rates
RATE="30.895"
THRESHOLD="32.0"

echo ""
echo "=== Testing bc Comparison ==="
if command -v bc >/dev/null 2>&1; then
    if [ "$(echo "$RATE <= $THRESHOLD" | bc -l)" -eq 1 ]; then
        echo "✅ bc comparison: $RATE <= $THRESHOLD (should send email)"
    else
        echo "📈 bc comparison: $RATE > $THRESHOLD (no email)"
    fi
else
    echo "bc not available, testing awk fallback"
    RATE_INT=$(echo "$RATE" | awk '{printf "%.0f", $1 * 1000}')
    THRESHOLD_INT=$(echo "$THRESHOLD" | awk '{printf "%.0f", $1 * 1000}')
    echo "Rate: $RATE -> $RATE_INT, Threshold: $THRESHOLD -> $THRESHOLD_INT"
    if [ "$RATE_INT" -le "$THRESHOLD_INT" ]; then
        echo "✅ awk comparison: $RATE <= $THRESHOLD (should send email)"
    else
        echo "📈 awk comparison: $RATE > $THRESHOLD (no email)"
    fi
fi

echo ""
echo "=== All Tests Complete ==="
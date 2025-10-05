#!/bin/bash

# USD Rate Scraper Demonstration
# Shows different ways to get the USD selling spot rate

echo "🏦 USD Rate Scraper - Demo"
echo "=========================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
URL="https://rate.bot.com.tw/xrt?Lang=en-US"

echo
echo "1️⃣  Basic Usage (Human-readable output):"
python3 "$SCRIPT_DIR/usd_rate_scraper.py" --url "$URL" --manual-fallback

echo
echo "2️⃣  Quiet Mode (Script-friendly output):"
python3 "$SCRIPT_DIR/usd_rate_scraper.py" --url "$URL" --manual-fallback --quiet

echo
echo "3️⃣  Using the Simple Shell Wrapper:"
"$SCRIPT_DIR/get_usd_rate.sh"

echo
echo "4️⃣  Rate Analysis:"
RATE=$("$SCRIPT_DIR/get_usd_rate.sh")
echo "Current Rate: $RATE TWD"

if command -v bc &> /dev/null; then
    if (( $(echo "$RATE < 30.0" | bc -l) )); then
        echo "Analysis: 🟢 Excellent rate for selling USD!"
    elif (( $(echo "$RATE < 30.5" | bc -l) )); then
        echo "Analysis: 🟡 Good rate for selling USD"
    elif (( $(echo "$RATE < 31.0" | bc -l) )); then
        echo "Analysis: 🟠 Average rate"
    else
        echo "Analysis: 🔴 Rate is relatively high"
    fi
else
    echo "Analysis: Install 'bc' for rate comparison features"
fi

echo
echo "5️⃣  Rate Calculation Example:"
echo "If you sell 100 USD at rate $RATE:"
if command -v bc &> /dev/null; then
    TWD_AMOUNT=$(echo "$RATE * 100" | bc)
    echo "You would receive: $TWD_AMOUNT TWD"
else
    echo "You would receive: $(echo "$RATE * 100" | python3 -c "import sys; print(float(sys.stdin.read().strip()))") TWD"
fi

echo
echo "6️⃣  Using in a Shell Script:"
cat << 'EOF'
# Example shell script usage:
RATE=$(./get_usd_rate.sh)
if [ $? -eq 0 ]; then
    echo "Current USD rate: $RATE TWD"
else
    echo "Failed to get rate"
fi
EOF

echo
echo "✅ Demo completed!"
echo "📖 See SIMPLE_README.md for more examples"
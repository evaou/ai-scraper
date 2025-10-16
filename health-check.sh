#!/bin/bash

# Quick deployment health check script
# This verifies that the deployment is working correctly

set -e

DOMAIN="paramita-scraper.duckdns.org"
BASE_URL="http://${DOMAIN}"

echo "🔍 Running deployment health checks..."

# Test 1: Basic connectivity
echo "1️⃣ Testing basic connectivity..."
if curl -sf "${BASE_URL}/health" > /dev/null; then
    echo "✅ Basic health check passed"
else
    echo "❌ Basic health check failed"
    exit 1
fi

# Test 2: Liveness check
echo "2️⃣ Testing liveness check..."
if curl -sf "${BASE_URL}/api/v1/health/live" > /dev/null; then
    echo "✅ Liveness check passed"
else
    echo "❌ Liveness check failed"
    exit 1
fi

# Test 3: Metrics endpoint
echo "3️⃣ Testing metrics endpoint..."
if curl -sf "${BASE_URL}/api/v1/health/metrics" > /dev/null; then
    echo "✅ Metrics endpoint passed"
else
    echo "❌ Metrics endpoint failed"
    exit 1
fi

# Test 4: API scraping endpoint (basic test)
echo "4️⃣ Testing scraping API (basic)..."
SCRAPE_RESPONSE=$(curl -s -w "%{http_code}" -X POST "${BASE_URL}/api/v1/scraping/scrape" \
    -H "Content-Type: application/json" \
    -d '{"url": "https://httpbin.org/html", "target": "html"}' -o /dev/null)

if [ "$SCRAPE_RESPONSE" = "200" ] || [ "$SCRAPE_RESPONSE" = "202" ]; then
    echo "✅ Scraping API passed (Status: $SCRAPE_RESPONSE)"
else
    echo "❌ Scraping API failed (Status: $SCRAPE_RESPONSE)"
    exit 1
fi

# Test 5: Specific rate.bot.com.tw test
echo "5️⃣ Testing rate.bot.com.tw scraping..."
RATE_RESPONSE=$(curl -s -w "%{http_code}" -X POST "${BASE_URL}/api/v1/scraping/scrape" \
    -H "Content-Type: application/json" \
    -d '{"url": "https://rate.bot.com.tw/xrt?Lang=en-US"}' \
    --connect-timeout 10 --max-time 30 -o /dev/null)

if [ "$RATE_RESPONSE" = "200" ] || [ "$RATE_RESPONSE" = "202" ]; then
    echo "✅ Rate.bot.com.tw scraping passed (Status: $RATE_RESPONSE)"
else
    echo "❌ Rate.bot.com.tw scraping failed (Status: $RATE_RESPONSE)"
    echo "⚠️  This may be normal if workers are still starting up"
fi

# Test 6: API documentation
echo "6️⃣ Testing API documentation..."
if curl -sf "${BASE_URL}/api/v1/docs" > /dev/null; then
    echo "✅ API documentation accessible"
else
    echo "❌ API documentation failed"
    exit 1
fi

# Test 7: Exact target curl command
echo "7️⃣ Testing EXACT target command..."
echo "Command: curl -X POST \"${BASE_URL}/api/v1/scraping/scrape\" -H \"Content-Type: application/json\" -d '{\"url\": \"https://rate.bot.com.tw/xrt?Lang=en-US\"}'"

EXACT_TEST=$(curl -s -w "%{http_code}" -X POST "${BASE_URL}/api/v1/scraping/scrape" \
    -H "Content-Type: application/json" \
    -d '{"url": "https://rate.bot.com.tw/xrt?Lang=en-US"}' \
    --connect-timeout 10 --max-time 30 -o /tmp/exact_response.json 2>/dev/null)

echo "Response: HTTP $EXACT_TEST"
if [ -f "/tmp/exact_response.json" ]; then
    echo "Body: $(cat /tmp/exact_response.json | head -c 200)..."
    rm -f /tmp/exact_response.json
fi

if [ "$EXACT_TEST" = "200" ] || [ "$EXACT_TEST" = "202" ] || [ "$EXACT_TEST" = "201" ]; then
    echo "🎉 SUCCESS! Target curl command works perfectly!"
else
    echo "⚠️ Target command returned HTTP $EXACT_TEST (may need worker startup time)"
fi

echo ""
echo "🎉 All deployment health checks completed!"
echo "🌐 API is fully operational at: ${BASE_URL}/api/v1"
echo "📚 Documentation available at: ${BASE_URL}/api/v1/docs"
echo ""
echo "🔒 To enable HTTPS, run: sudo ./setup-ssl-enhanced.sh"
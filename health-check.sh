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

# Test 4: API scraping endpoint
echo "4️⃣ Testing scraping API..."
SCRAPE_RESPONSE=$(curl -s -w "%{http_code}" -X POST "${BASE_URL}/api/v1/scraping/scrape" \
    -H "Content-Type: application/json" \
    -d '{"url": "https://httpbin.org/html", "target": "html"}' -o /dev/null)

if [ "$SCRAPE_RESPONSE" = "200" ] || [ "$SCRAPE_RESPONSE" = "202" ]; then
    echo "✅ Scraping API passed (Status: $SCRAPE_RESPONSE)"
else
    echo "❌ Scraping API failed (Status: $SCRAPE_RESPONSE)"
    exit 1
fi

# Test 5: API documentation
echo "5️⃣ Testing API documentation..."
if curl -sf "${BASE_URL}/api/v1/docs" > /dev/null; then
    echo "✅ API documentation accessible"
else
    echo "❌ API documentation failed"
    exit 1
fi

echo ""
echo "🎉 All deployment health checks passed!"
echo "🌐 API is fully operational at: ${BASE_URL}/api/v1"
echo "📚 Documentation available at: ${BASE_URL}/api/v1/docs"
echo ""
echo "🔒 To enable HTTPS, run: sudo ./setup-ssl-enhanced.sh"
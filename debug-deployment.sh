#!/bin/bash

# Debug deployment issues script
# Run this script to diagnose deployment problems

echo "🔍 AI Scraper Deployment Diagnostics"
echo "===================================="

# Check if in correct directory
if [ ! -f "docker-compose.prod.yml" ]; then
    echo "❌ Error: docker-compose.prod.yml not found"
    echo "Please run this script from the ai-scraper directory"
    exit 1
fi

echo ""
echo "1️⃣ Container Status:"
echo "--------------------"
docker compose -f docker-compose.prod.yml ps

echo ""
echo "2️⃣ Service Health Checks:"
echo "-------------------------"

# Test database
echo -n "Database: "
if docker compose -f docker-compose.prod.yml exec -T db pg_isready -U scraper_user -d scraper_prod > /dev/null 2>&1; then
    echo "✅ Healthy"
else
    echo "❌ Unhealthy"
fi

# Test Redis
echo -n "Redis: "
if docker compose -f docker-compose.prod.yml exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Healthy"
else
    echo "❌ Unhealthy"
fi

# Test API directly
echo -n "API (Direct): "
if docker compose -f docker-compose.prod.yml exec -T api curl -f -s http://localhost:8000/api/v1/health/live > /dev/null 2>&1; then
    echo "✅ Healthy"
else
    echo "❌ Unhealthy"
fi

# Test Nginx
echo -n "Nginx: "
if docker compose -f docker-compose.prod.yml ps nginx | grep -q "Up"; then
    echo "✅ Running"
else
    echo "❌ Not Running"
fi

# Test Nginx proxy
echo -n "Nginx Proxy: "
if curl -f -s -m 5 http://localhost/health > /dev/null 2>&1; then
    echo "✅ Healthy"
else
    echo "❌ Unhealthy"
fi

echo ""
echo "3️⃣ Network Connectivity:"
echo "------------------------"

# Test external connectivity
echo -n "External (via domain): "
if curl -f -s -m 10 http://paramita-scraper.duckdns.org/health > /dev/null 2>&1; then
    echo "✅ Accessible"
else
    echo "❌ Not Accessible"
fi

echo ""
echo "4️⃣ Key Endpoints Test:"
echo "----------------------"

# Health endpoint
echo -n "/health: "
HEALTH_CODE=$(curl -s -o /dev/null -w "%{http_code}" -m 5 http://localhost/health 2>/dev/null)
echo "HTTP $HEALTH_CODE"

# Metrics endpoint
echo -n "/api/v1/health/metrics: "
METRICS_CODE=$(curl -s -o /dev/null -w "%{http_code}" -m 5 http://localhost/api/v1/health/metrics 2>/dev/null)
echo "HTTP $METRICS_CODE"

# API docs
echo -n "/api/v1/docs: "
DOCS_CODE=$(curl -s -o /dev/null -w "%{http_code}" -m 5 http://localhost/api/v1/docs 2>/dev/null)
echo "HTTP $DOCS_CODE"

echo ""
echo "5️⃣ Recent Logs (Last 10 lines each):"
echo "------------------------------------"

echo ""
echo "📋 API Logs:"
docker compose -f docker-compose.prod.yml logs api --tail=10 2>/dev/null || echo "Could not fetch API logs"

echo ""
echo "🌐 Nginx Logs:"
docker compose -f docker-compose.prod.yml logs nginx --tail=10 2>/dev/null || echo "Could not fetch Nginx logs"

echo ""
echo "6️⃣ Configuration Check:"
echo "-----------------------"

echo -n "Nginx config syntax: "
if docker compose -f docker-compose.prod.yml exec -T nginx nginx -t > /dev/null 2>&1; then
    echo "✅ Valid"
else
    echo "❌ Invalid"
    docker compose -f docker-compose.prod.yml exec -T nginx nginx -t 2>&1 | head -5
fi

echo ""
echo "🎯 Diagnosis Complete!"
echo ""
echo "🎯 Test Specific Target Command:"
echo "curl -X POST \"http://paramita-scraper.duckdns.org/api/v1/scraping/scrape\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"url\": \"https://rate.bot.com.tw/xrt?Lang=en-US\"}' \\"
echo "  --connect-timeout 10 --max-time 30"
echo ""
echo "💡 Quick Fixes:"
echo "  - If containers are not running: docker compose -f docker-compose.prod.yml up -d"
echo "  - If nginx config invalid: check docker/nginx/nginx.conf"
echo "  - If external access fails: check domain DNS and server firewall"
echo "  - For full deployment: ./scripts/deploy.sh"
echo "  - For comprehensive testing: ./health-check.sh"
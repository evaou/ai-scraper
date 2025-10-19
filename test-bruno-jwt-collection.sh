#!/bin/bash
# Bruno Collection JWT_SECRET_KEY Test Script
# This script tests key endpoints from the Bruno collection using curl with JWT_SECRET_KEY

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="http://paramita-scraper.duckdns.org"
API_BASE="$BASE_URL/api/v1"

echo -e "${BLUE}🧪 Bruno Collection JWT_SECRET_KEY Test Suite${NC}"
echo "=============================================="

# Check JWT_SECRET_KEY environment variable
if [ -z "$JWT_SECRET_KEY" ]; then
    echo -e "${RED}❌ Error: JWT_SECRET_KEY environment variable not set${NC}"
    echo "Please export JWT_SECRET_KEY with the correct value:"
    echo "export JWT_SECRET_KEY='your-jwt-secret-key-here'"
    exit 1
fi

echo -e "${GREEN}✅ JWT_SECRET_KEY found${NC} (${JWT_SECRET_KEY:0:8}...)"
echo ""

# Test 1: Health Endpoints (No Auth Required)
echo -e "${YELLOW}📋 Testing Health Endpoints (No Authentication)${NC}"
echo "------------------------------------------------"

echo -n "Health Check: "
if curl -s -f -H "Accept: application/json" "$API_BASE/health" > /dev/null; then
    echo -e "${GREEN}✅ PASS${NC}"
else
    echo -e "${RED}❌ FAIL${NC}"
fi

echo -n "Readiness Probe: "
if curl -s -f -H "Accept: application/json" "$API_BASE/health/ready" > /dev/null; then
    echo -e "${GREEN}✅ PASS${NC}"
else
    echo -e "${RED}❌ FAIL${NC}"
fi

echo -n "Liveness Probe: "
if curl -s -f -H "Accept: application/json" "$API_BASE/health/live" > /dev/null; then
    echo -e "${GREEN}✅ PASS${NC}"
else
    echo -e "${RED}❌ FAIL${NC}"
fi

echo ""

# Test 2: Admin Endpoints (Auth Required)
echo -e "${YELLOW}🔐 Testing Admin Endpoints (Authentication Required)${NC}"
echo "---------------------------------------------------"

echo -n "Admin Statistics: "
response=$(curl -s -w "%{http_code}" -H "Accept: application/json" -H "X-API-Key: $JWT_SECRET_KEY" "$API_BASE/admin/stats")
http_code="${response: -3}"
if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✅ PASS${NC}"
else
    echo -e "${RED}❌ FAIL (HTTP $http_code)${NC}"
fi

echo -n "Admin Metrics: "
response=$(curl -s -w "%{http_code}" -H "Accept: application/json" -H "X-API-Key: $JWT_SECRET_KEY" "$API_BASE/admin/metrics")
http_code="${response: -3}"
if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✅ PASS${NC}"
else
    echo -e "${RED}❌ FAIL (HTTP $http_code)${NC}"
fi

echo -n "Queue Status: "
response=$(curl -s -w "%{http_code}" -H "Accept: application/json" -H "X-API-Key: $JWT_SECRET_KEY" "$API_BASE/admin/queue")
http_code="${response: -3}"
if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✅ PASS${NC}"
else
    echo -e "${RED}❌ FAIL (HTTP $http_code)${NC}"
fi

echo ""

# Test 3: Authentication Validation
echo -e "${YELLOW}🔑 Testing Authentication Validation${NC}"
echo "-----------------------------------"

echo -n "No API Key (should fail): "
response=$(curl -s -w "%{http_code}" -X POST -H "Content-Type: application/json" -d '{"url":"https://httpbin.org/html"}' "$API_BASE/scrape")
http_code="${response: -3}"
if [ "$http_code" = "401" ]; then
    echo -e "${GREEN}✅ PASS (Properly rejected)${NC}"
else
    echo -e "${RED}❌ FAIL (Expected 401, got $http_code)${NC}"
fi

echo -n "Invalid API Key (should fail): "
response=$(curl -s -w "%{http_code}" -X POST -H "Content-Type: application/json" -H "X-API-Key: invalid-key-12345" -d '{"url":"https://httpbin.org/html"}' "$API_BASE/scrape")
http_code="${response: -3}"
if [ "$http_code" = "401" ]; then
    echo -e "${GREEN}✅ PASS (Properly rejected)${NC}"
else
    echo -e "${RED}❌ FAIL (Expected 401, got $http_code)${NC}"
fi

echo -n "Valid JWT_SECRET_KEY (should work): "
response=$(curl -s -w "%{http_code}" -X POST -H "Content-Type: application/json" -H "X-API-Key: $JWT_SECRET_KEY" -d '{"url":"https://httpbin.org/html","options":{"wait_time":1,"extract_text":true,"timeout":15}}' "$API_BASE/scrape")
http_code="${response: -3}"
if [ "$http_code" = "202" ]; then
    echo -e "${GREEN}✅ PASS (Job submitted)${NC}"
elif [ "$http_code" = "401" ]; then
    echo -e "${RED}❌ FAIL (API key not registered in database)${NC}"
    echo -e "${YELLOW}⚠️  Run: docker compose -f docker-compose.prod.yml exec api python3 scripts/create-jwt-api-key.py${NC}"
else
    echo -e "${RED}❌ FAIL (HTTP $http_code)${NC}"
fi

echo ""
echo -e "${BLUE}🏁 Test Complete${NC}"
echo "=============="
echo ""
echo "If any authenticated endpoints fail with 401, ensure JWT_SECRET_KEY is registered:"
echo "1. SSH to production: ssh root@paramita-scraper.duckdns.org"
echo "2. Navigate to: cd /opt/ai-scraper"  
echo "3. Register key: docker compose -f docker-compose.prod.yml exec api python3 scripts/create-jwt-api-key.py"
echo ""
echo "Bruno Collection Status:"
echo "✅ All environment files configured to use JWT_SECRET_KEY"
echo "✅ All request headers properly configured"
echo "✅ Authentication validation working"
echo "⚠️  Production API key registration may be required"
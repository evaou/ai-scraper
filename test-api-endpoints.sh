#!/bin/bash

# API Testing Script
# Tests all endpoints to verify authentication requirements

echo "🧪 AI Scraper API Test Suite"
echo "============================="
echo ""

# Base URL
BASE_URL="http://paramita-scraper.duckdns.org/api/v1"

# Test JWT key (you should set this to your actual JWT_SECRET_KEY)
JWT_KEY="${JWT_SECRET_KEY:-test-key}"

# Function to test endpoint
test_endpoint() {
    local method="$1"
    local path="$2"
    local auth_required="$3"
    local description="$4"
    local data="$5"
    
    echo "📡 Testing: $method $path"
    echo "   Description: $description"
    echo "   Expected Auth: $auth_required"
    
    # Test without auth
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\nHTTP_CODE:%{http_code}\n" "$BASE_URL$path")
    elif [ "$method" = "POST" ]; then
        if [ -n "$data" ]; then
            response=$(curl -s -w "\nHTTP_CODE:%{http_code}\n" -X POST -H "Content-Type: application/json" -d "$data" "$BASE_URL$path")
        else
            response=$(curl -s -w "\nHTTP_CODE:%{http_code}\n" -X POST "$BASE_URL$path")
        fi
    elif [ "$method" = "DELETE" ]; then
        response=$(curl -s -w "\nHTTP_CODE:%{http_code}\n" -X DELETE "$BASE_URL$path")
    fi
    
    http_code=$(echo "$response" | tail -1 | sed 's/HTTP_CODE://')
    response_body=$(echo "$response" | head -n -1)
    
    echo "   Without Auth: HTTP $http_code"
    
    # Test with auth if required
    if [ "$auth_required" = "Yes" ]; then
        if [ "$method" = "GET" ]; then
            auth_response=$(curl -s -w "\nHTTP_CODE:%{http_code}\n" -H "X-API-Key: $JWT_KEY" "$BASE_URL$path")
        elif [ "$method" = "POST" ]; then
            if [ -n "$data" ]; then
                auth_response=$(curl -s -w "\nHTTP_CODE:%{http_code}\n" -X POST -H "Content-Type: application/json" -H "X-API-Key: $JWT_KEY" -d "$data" "$BASE_URL$path")
            else
                auth_response=$(curl -s -w "\nHTTP_CODE:%{http_code}\n" -X POST -H "X-API-Key: $JWT_KEY" "$BASE_URL$path")
            fi
        elif [ "$method" = "DELETE" ]; then
            auth_response=$(curl -s -w "\nHTTP_CODE:%{http_code}\n" -X DELETE -H "X-API-Key: $JWT_KEY" "$BASE_URL$path")
        fi
        
        auth_http_code=$(echo "$auth_response" | tail -1 | sed 's/HTTP_CODE://')
        echo "   With Auth: HTTP $auth_http_code"
        
        # Check if authentication works as expected
        if [ "$http_code" = "401" ] && [ "$auth_http_code" != "401" ]; then
            echo "   ✅ Authentication working correctly"
        elif [ "$http_code" != "401" ]; then
            echo "   ⚠️ WARNING: Endpoint allows access without authentication"
        elif [ "$auth_http_code" = "401" ]; then
            echo "   ❌ Authentication failed - check JWT key"
        fi
    else
        # Check if endpoint incorrectly requires auth
        if [ "$http_code" = "401" ]; then
            echo "   ❌ ERROR: Endpoint requires auth but shouldn't"
        else
            echo "   ✅ Public endpoint working correctly"
        fi
    fi
    
    # Show response for errors
    if [ "$http_code" = "500" ] || [ "$http_code" = "422" ] || [ "$http_code" = "400" ]; then
        echo "   Response: $(echo "$response_body" | head -c 200)"
    fi
    
    echo ""
}

echo "🔑 Using JWT Key: ${JWT_KEY:0:10}..." 
echo ""

# Health endpoints
echo "🏥 HEALTH ENDPOINTS"
echo "==================="
test_endpoint "GET" "/health" "No" "Main health check"
test_endpoint "GET" "/health/ready" "No" "Readiness probe"
test_endpoint "GET" "/health/live" "No" "Liveness probe"

# System endpoints  
echo "📊 SYSTEM ENDPOINTS"
echo "==================="
test_endpoint "GET" "/version" "No" "API version info"
test_endpoint "GET" "/metrics" "No" "System metrics"
test_endpoint "GET" "/stats" "No" "System statistics"

# Scraping endpoints
echo "🕷️ SCRAPING ENDPOINTS"
echo "====================="
test_endpoint "POST" "/scrape" "Yes" "Submit scraping job" '{"url": "https://httpbin.org/html"}'
test_endpoint "GET" "/scrape/00000000-0000-0000-0000-000000000000" "No" "Get job status (fake ID)"
test_endpoint "DELETE" "/scrape/00000000-0000-0000-0000-000000000000" "No" "Cancel job (fake ID)"
test_endpoint "GET" "/results?limit=5" "No" "List recent results"

# Admin endpoints
echo "👨‍💼 ADMIN ENDPOINTS" 
echo "=================="
test_endpoint "GET" "/admin/stats" "No" "Admin statistics"
test_endpoint "GET" "/admin/queue" "No" "Queue status"
test_endpoint "GET" "/admin/metrics" "No" "Admin metrics"
test_endpoint "POST" "/admin/cleanup" "No" "Cleanup old jobs"

echo "🎯 TEST SUMMARY"
echo "==============="
echo "Endpoints tested: 13"
echo ""
echo "Expected authentication:"
echo "• POST /scrape - Should require X-API-Key header"
echo "• All other endpoints - Should be public"
echo ""
echo "If you see authentication failures, run:"
echo "export JWT_SECRET_KEY='your-actual-jwt-key'"
echo "./test-api-endpoints.sh"
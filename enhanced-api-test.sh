#!/bin/bash

# Enhanced API Testing Script with Configuration Detection
# Tests all endpoints and detects API configuration mode

echo "🔍 AI Scraper API Analysis & Testing"
echo "===================================="
echo ""

# Base URL
BASE_URL="http://paramita-scraper.duckdns.org/api/v1"

# Test JWT key (you should set this to your actual JWT_SECRET_KEY)
JWT_KEY="${JWT_SECRET_KEY:-sample-test-key}"

# Function to check API configuration mode
check_api_mode() {
    echo "🔧 Detecting API Configuration Mode"
    echo "===================================="
    
    # Test scrape endpoint without auth
    echo "Testing /scrape without authentication..."
    response=$(curl -s -w "\nHTTP_CODE:%{http_code}\n" -X POST \
        -H "Content-Type: application/json" \
        -d '{"url": "https://httpbin.org/html"}' \
        "$BASE_URL/scrape")
    
    http_code=$(echo "$response" | tail -1 | sed 's/HTTP_CODE://')
    response_body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "401" ]; then
        echo "   ✅ API_KEY_REQUIRED=true (Secure mode)"
        echo "   📝 Authentication required for /scrape endpoint"
        API_MODE="secure"
    elif [ "$http_code" = "202" ] || [ "$http_code" = "200" ]; then
        echo "   ⚠️ API_KEY_REQUIRED=false (Open mode)"
        echo "   📝 No authentication required"
        API_MODE="open"
    else
        echo "   ❓ Unknown mode (HTTP $http_code)"
        echo "   Response: $(echo "$response_body" | head -c 200)"
        API_MODE="unknown"
    fi
    echo ""
}

# Function to test endpoint with detailed analysis
test_endpoint() {
    local method="$1"
    local path="$2"
    local description="$3"
    local data="$4"
    local expect_auth="$5"
    
    echo "📡 $method $path"
    echo "   $description"
    
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
    
    # Analyze response
    case "$http_code" in
        200|202) echo "   ✅ Working (HTTP $http_code)" ;;
        404) echo "   ⚠️ Not found (HTTP $http_code) - Expected for test ID" ;;
        401) echo "   🔒 Requires authentication (HTTP $http_code)" ;;
        500) echo "   ❌ Server error (HTTP $http_code)" ;;
        422) echo "   ❌ Validation error (HTTP $http_code)" ;;
        *) echo "   ❓ Unexpected response (HTTP $http_code)" ;;
    esac
    
    # Show error details for server errors
    if [ "$http_code" = "500" ] || [ "$http_code" = "422" ]; then
        echo "   📋 Error details: $(echo "$response_body" | jq -r '.message // .detail // .' 2>/dev/null || echo "$response_body" | head -c 200)"
    fi
    
    # Test with auth if endpoint returned 401
    if [ "$http_code" = "401" ] && [ "$expect_auth" = "yes" ]; then
        echo "   🔑 Testing with API key..."
        if [ "$method" = "GET" ]; then
            auth_response=$(curl -s -w "\nHTTP_CODE:%{http_code}\n" -H "X-API-Key: $JWT_KEY" "$BASE_URL$path")
        elif [ "$method" = "POST" ]; then
            if [ -n "$data" ]; then
                auth_response=$(curl -s -w "\nHTTP_CODE:%{http_code}\n" -X POST -H "Content-Type: application/json" -H "X-API-Key: $JWT_KEY" -d "$data" "$BASE_URL$path")
            else
                auth_response=$(curl -s -w "\nHTTP_CODE:%{http_code}\n" -X POST -H "X-API-Key: $JWT_KEY" "$BASE_URL$path")
            fi
        fi
        
        auth_http_code=$(echo "$auth_response" | tail -1 | sed 's/HTTP_CODE://')
        auth_body=$(echo "$auth_response" | head -n -1)
        
        case "$auth_http_code" in
            200|202) echo "   ✅ Authentication successful (HTTP $auth_http_code)" ;;
            401) echo "   ❌ Authentication failed - Invalid JWT key (HTTP $auth_http_code)" ;;
            *) echo "   ❓ Unexpected auth response (HTTP $auth_http_code)" ;;
        esac
        
        if [ "$auth_http_code" = "401" ]; then
            echo "   📋 Auth error: $(echo "$auth_body" | jq -r '.message // .detail // .' 2>/dev/null || echo "$auth_body" | head -c 200)"
        fi
    fi
    
    echo ""
}

# Run configuration detection
check_api_mode

echo "🧪 Testing All API Endpoints"
echo "============================="
echo ""

# Health endpoints
echo "🏥 Health & System Endpoints"
echo "----------------------------"
test_endpoint "GET" "/health" "Main health check" "" "no"
test_endpoint "GET" "/health/ready" "Readiness probe" "" "no"
test_endpoint "GET" "/health/live" "Liveness probe" "" "no"
test_endpoint "GET" "/version" "API version" "" "no"
test_endpoint "GET" "/metrics" "System metrics" "" "no"
test_endpoint "GET" "/stats" "System statistics" "" "no"

# Scraping endpoints
echo "🕷️ Scraping Endpoints"
echo "---------------------"
if [ "$API_MODE" = "secure" ]; then
    test_endpoint "POST" "/scrape" "Submit scraping job" '{"url": "https://httpbin.org/html"}' "yes"
else
    test_endpoint "POST" "/scrape" "Submit scraping job" '{"url": "https://httpbin.org/html"}' "no"
fi
test_endpoint "GET" "/scrape/00000000-0000-0000-0000-000000000000" "Get job status" "" "no"
test_endpoint "DELETE" "/scrape/00000000-0000-0000-0000-000000000000" "Cancel job" "" "no"
test_endpoint "GET" "/results?limit=5" "List recent results" "" "no"

# Admin endpoints
echo "👨‍💼 Admin Endpoints"
echo "-------------------"
test_endpoint "GET" "/admin/stats" "Admin statistics" "" "no"
test_endpoint "GET" "/admin/queue" "Queue status" "" "no"
test_endpoint "GET" "/admin/metrics" "Admin metrics" "" "no"
test_endpoint "POST" "/admin/cleanup" "Cleanup old jobs" "" "no"

echo "📊 Summary & Recommendations"
echo "============================"
echo ""

if [ "$API_MODE" = "secure" ]; then
    echo "✅ Current Mode: SECURE (API_KEY_REQUIRED=true)"
    echo "   • POST /scrape requires valid API key"
    echo "   • All other endpoints are public"
    echo "   • This is the recommended production configuration"
    echo ""
    echo "🔧 To test with authentication:"
    echo "   export JWT_SECRET_KEY='your-actual-jwt-secret-key'"
    echo "   $0"
elif [ "$API_MODE" = "open" ]; then
    echo "⚠️ Current Mode: OPEN (API_KEY_REQUIRED=false)"
    echo "   • All endpoints are public (no authentication)"
    echo "   • Consider enabling API_KEY_REQUIRED=true for production"
    echo ""
    echo "🔧 To enable secure mode:"
    echo "   1. Set API_KEY_REQUIRED=true in environment"
    echo "   2. Register your JWT_SECRET_KEY using:"
    echo "      ./trigger-jwt-deployment.sh"
else
    echo "❓ Current Mode: UNKNOWN"
    echo "   • API behavior is unexpected"
    echo "   • Check server logs for issues"
fi

echo ""
echo "🔍 Issues Found:"
if curl -s -X POST "$BASE_URL/admin/cleanup" | grep -q "Failed to cleanup"; then
    echo "   ❌ Admin cleanup endpoint has server errors"
    echo "      This needs investigation in server logs"
else
    echo "   ✅ No major issues detected"
fi

echo ""
echo "📖 Full API Documentation:"
echo "   http://paramita-scraper.duckdns.org/api/v1/docs"
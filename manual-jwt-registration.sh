#!/bin/bash

# Manual JWT Key Registration Script
# Run this script to manually register the JWT_SECRET_KEY as an API key

echo "🔑 Manual JWT Key Registration"
echo "=============================="
echo ""

# Check if JWT_SECRET_KEY is available
if [ -z "$JWT_SECRET_KEY" ]; then
    echo "❌ Error: JWT_SECRET_KEY environment variable not set"
    echo ""
    echo "💡 To fix this, run:"
    echo "export JWT_SECRET_KEY='your-jwt-secret-here'"
    echo ""
    echo "🔍 To get your JWT secret, check your GitHub repository secrets"
    echo "   or generate a new one with: openssl rand -base64 32"
    exit 1
fi

echo "✅ JWT_SECRET_KEY configured: ${JWT_SECRET_KEY:0:8}..."
echo ""

# Test if docker compose is available
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker not found"
    exit 1
fi

# Check if docker-compose.prod.yml exists
if [ ! -f "docker-compose.prod.yml" ]; then
    echo "❌ Error: docker-compose.prod.yml not found"
    echo "   Please run this script from the ai-scraper project root"
    exit 1
fi

echo "🐳 Attempting to register JWT key in production database..."
echo ""

# Run the registration script
if docker compose -f docker-compose.prod.yml exec -e JWT_SECRET_KEY="$JWT_SECRET_KEY" api python3 scripts/create-jwt-api-key.py; then
    echo ""
    echo "🎉 SUCCESS! JWT key registration completed"
    echo ""
    echo "🧪 Testing API authentication..."
    
    # Test the API authentication
    API_TEST=$(curl -s -w "%{http_code}" -X POST http://paramita-scraper.duckdns.org/api/v1/scrape \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $JWT_SECRET_KEY" \
        -d '{"url": "https://httpbin.org/html"}' 2>/dev/null || echo "000")
    
    HTTP_CODE="${API_TEST: -3}"
    if [ "$HTTP_CODE" = "202" ]; then
        echo "✅ API authentication working! Enhanced mode is now active."
        echo ""
        echo "🚀 Your GitHub Actions workflows will now use:"
        echo "   • USD Rate Email: Enhanced API mode"
        echo "   • Stock Price Alert: Enhanced API mode"
    else
        echo "⚠️ API test failed (HTTP: $HTTP_CODE)"
        echo "   Registration may not have worked correctly"
    fi
else
    echo ""
    echo "❌ FAILED: JWT key registration failed"
    echo ""
    echo "🔍 Troubleshooting steps:"
    echo "1. Check if containers are running: docker compose -f docker-compose.prod.yml ps"
    echo "2. Check container logs: docker compose -f docker-compose.prod.yml logs api"
    echo "3. Verify database connection: docker compose -f docker-compose.prod.yml exec api python3 -c 'import asyncio; from app.core.database import engine; print(\"DB OK\")'"
fi

echo ""
echo "📋 Manual Registration Complete"
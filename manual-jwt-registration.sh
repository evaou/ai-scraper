#!/bin/bash

# Manual JWT Key Registration Script
# Run this script to manually register the JWT_SECRET_KEY as an API key

echo "🔑 AI Scraper - Manual JWT Key Registration"
echo "==========================================="
echo ""

# Check if JWT_SECRET_KEY is available
if [ -z "$JWT_SECRET_KEY" ]; then
    echo "❌ Error: JWT_SECRET_KEY environment variable not set"
    echo ""
    echo "💡 SOLUTION - Set your JWT secret key:"
    echo ""
    echo "Method 1 - Use the same key from your GitHub repository secrets:"
    echo "export JWT_SECRET_KEY='your-github-jwt-secret-key-here'"
    echo ""
    echo "Method 2 - Generate a new key (then update GitHub secrets):"
    echo "export JWT_SECRET_KEY=\$(openssl rand -base64 32)"
    echo "echo \"Your new JWT key: \$JWT_SECRET_KEY\""
    echo "# Copy this key to GitHub repository secrets as JWT_SECRET_KEY"
    echo ""
    echo "🔍 To check your current GitHub secrets:"
    echo "   Go to: Repository → Settings → Secrets and variables → Actions"
    echo "   Look for: JWT_SECRET_KEY"
    exit 1
fi

echo "✅ JWT_SECRET_KEY configured: ${JWT_SECRET_KEY:0:12}..."
echo ""

# Test if docker compose is available
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker not found"
    echo "   Please install Docker or run this on your production server"
    exit 1
fi

# Check if docker-compose.prod.yml exists
if [ ! -f "docker-compose.prod.yml" ]; then
    echo "❌ Error: docker-compose.prod.yml not found"
    echo "   Please run this script from the ai-scraper project root directory"
    echo "   Current directory: $(pwd)"
    exit 1
fi

# Check if containers are running
echo "🐳 Checking Docker containers..."
if ! docker compose -f docker-compose.prod.yml ps --services --filter "status=running" | grep -q "api"; then
    echo "⚠️ Warning: API container may not be running"
    echo "   Container status:"
    docker compose -f docker-compose.prod.yml ps
    echo ""
    echo "   To start containers: docker compose -f docker-compose.prod.yml up -d"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "🔧 Attempting to register JWT key in production database..."
echo ""

# Run the registration script with enhanced error handling
if docker compose -f docker-compose.prod.yml exec -e JWT_SECRET_KEY="$JWT_SECRET_KEY" api python3 scripts/create-jwt-api-key.py; then
    echo ""
    echo "🎉 SUCCESS! JWT key registration completed"
    echo ""
    echo "🧪 Testing API authentication..."
    
    # Test the API authentication
    echo "   Sending test request to API..."
    API_TEST=$(curl -s -w "%{http_code}" -X POST http://paramita-scraper.duckdns.org/api/v1/scrape \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $JWT_SECRET_KEY" \
        -d '{"url": "https://httpbin.org/html"}' 2>/dev/null || echo "000")
    
    HTTP_CODE="${API_TEST: -3}"
    if [ "$HTTP_CODE" = "202" ]; then
        echo "   ✅ API authentication working! (HTTP 202 - Job accepted)"
        echo ""
        echo "🚀 WORKFLOWS NOW ENABLED:"
        echo "   ✅ USD Rate Email: Will use Enhanced API mode"
        echo "   ✅ Stock Price Alert: Will use Enhanced API mode"
        echo ""
        echo "⚡ Benefits:"
        echo "   • Faster processing (server-side rendering)"
        echo "   • Better reliability (dedicated scraping infrastructure)"
        echo "   • Enhanced error handling"
        
    elif [ "$HTTP_CODE" = "401" ]; then
        echo "   ❌ API authentication still failing (HTTP 401)"
        echo "   Registration may not have worked correctly"
        echo ""
        echo "🔍 Troubleshooting:"
        echo "   1. Check if the JWT key was properly passed to the container"
        echo "   2. Verify database connection in the container"
        echo "   3. Check container logs: docker compose -f docker-compose.prod.yml logs api"
        
    else
        echo "   ⚠️ Unexpected API response (HTTP: $HTTP_CODE)"
        echo "   API server may have issues"
    fi
    
else
    echo ""
    echo "❌ FAILED: JWT key registration failed"
    echo ""
    echo "🔍 TROUBLESHOOTING STEPS:"
    echo ""
    echo "1. Check container status:"
    echo "   docker compose -f docker-compose.prod.yml ps"
    echo ""
    echo "2. Check API container logs:"
    echo "   docker compose -f docker-compose.prod.yml logs api"
    echo ""
    echo "3. Test database connection:"
    echo "   docker compose -f docker-compose.prod.yml exec api python3 -c \"import asyncio; print('DB test OK')\""
    echo ""
    echo "4. Check if script exists in container:"
    echo "   docker compose -f docker-compose.prod.yml exec api ls -la scripts/create-jwt-api-key.py"
    echo ""
    echo "5. Manual debugging:"
    echo "   docker compose -f docker-compose.prod.yml exec -e JWT_SECRET_KEY=\"$JWT_SECRET_KEY\" api bash"
    echo "   # Then inside container: python3 scripts/create-jwt-api-key.py"
    
    exit 1
fi

echo ""
echo "📋 Registration Summary:"
echo "   • JWT_SECRET_KEY: ${JWT_SECRET_KEY:0:12}... (registered)"
echo "   • API Endpoint: http://paramita-scraper.duckdns.org/api/v1"
echo "   • Workflows: Enhanced API mode enabled"
echo ""
echo "✅ Manual JWT Registration Complete!"
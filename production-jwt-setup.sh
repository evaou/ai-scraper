#!/bin/bash

# Production Server Setup Script
# Run this script ON YOUR PRODUCTION SERVER to fix JWT key registration

echo "🚀 AI Scraper - Production JWT Setup"
echo "===================================="
echo ""

# Check if we're on the production server
if ! command -v docker &> /dev/null; then
    echo "❌ ERROR: This script must be run on your production server"
    echo ""
    echo "📋 INSTRUCTIONS:"
    echo "1. SSH to your production server:"
    echo "   ssh user@paramita-scraper.duckdns.org"
    echo ""
    echo "2. Navigate to the ai-scraper directory:"
    echo "   cd /opt/ai-scraper  # or wherever your project is located"
    echo ""
    echo "3. Run this script on the server:"
    echo "   ./production-jwt-setup.sh"
    echo ""
    exit 1
fi

echo "✅ Docker found - proceeding with production setup..."
echo ""

# Check if .env.prod exists, if not create it
if [ ! -f ".env.prod" ]; then
    echo "⚠️ .env.prod not found - creating from environment variables..."
    echo ""
    
    # Check if we can get environment variables from the running container
    if docker compose -f docker-compose.prod.yml ps --services --filter "status=running" | grep -q "api"; then
        echo "📋 Extracting configuration from running container..."
        
        # Create basic .env.prod file
        cat > .env.prod << 'EOF'
# Production Environment Variables
# Generated automatically

# Database Configuration  
POSTGRES_DB=scraper_prod
POSTGRES_USER=scraper_user
POSTGRES_PASSWORD=your_secure_password_here
DATABASE_URL=postgresql+asyncpg://scraper_user:your_secure_password_here@db:5432/scraper_prod

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password_here
REDIS_DB=0
REDIS_URL=redis://:your_redis_password_here@redis:6379/0

# Security
JWT_SECRET_KEY=placeholder_will_be_updated
API_KEY_REQUIRED=true

# Application
ENVIRONMENT=production
LOG_LEVEL=INFO
EOF
        
        echo "✅ Basic .env.prod created"
        echo "⚠️ You may need to update passwords and database credentials"
        
    else
        echo "❌ No running containers found. Please start the application first:"
        echo "   docker compose -f docker-compose.prod.yml up -d"
        exit 1
    fi
else
    echo "✅ .env.prod found"
fi

# Update JWT_SECRET_KEY in .env.prod if provided
if [ -n "$JWT_SECRET_KEY" ]; then
    echo "🔧 Updating JWT_SECRET_KEY in .env.prod..."
    
    # Update or add JWT_SECRET_KEY to .env.prod
    if grep -q "^JWT_SECRET_KEY=" .env.prod; then
        sed -i "s/^JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$JWT_SECRET_KEY/" .env.prod
    else
        echo "JWT_SECRET_KEY=$JWT_SECRET_KEY" >> .env.prod
    fi
    
    echo "✅ JWT_SECRET_KEY updated in .env.prod"
else
    echo "⚠️ JWT_SECRET_KEY not provided as environment variable"
    echo "   Set it with: export JWT_SECRET_KEY='your-key-here'"
fi

# Restart containers with updated environment
echo ""
echo "🔄 Restarting containers with updated configuration..."
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d

# Wait for containers to start
echo "⏳ Waiting for containers to start..."
sleep 30

# Check container status
echo ""
echo "📊 Container Status:"
docker compose -f docker-compose.prod.yml ps

# Check if API container is running
if ! docker compose -f docker-compose.prod.yml ps --services --filter "status=running" | grep -q "api"; then
    echo ""
    echo "❌ API container is not running. Check logs:"
    echo "   docker compose -f docker-compose.prod.yml logs api"
    exit 1
fi

# Check if script exists in container
echo ""
echo "🔍 Checking if JWT registration script exists in container..."
if docker compose -f docker-compose.prod.yml exec api ls -la scripts/create-jwt-api-key.py > /dev/null 2>&1; then
    echo "✅ JWT registration script found in container"
else
    echo "❌ JWT registration script not found in container"
    echo ""
    echo "🔄 This means the container image is outdated. Options:"
    echo ""
    echo "Option 1 - Rebuild containers with latest code:"
    echo "   docker compose -f docker-compose.prod.yml build --no-cache"
    echo "   docker compose -f docker-compose.prod.yml up -d"
    echo ""
    echo "Option 2 - Trigger a new deployment from GitHub:"
    echo "   Push any commit to main branch to trigger deployment"
    echo ""
    exit 1
fi

# Now try to register the JWT key
if [ -n "$JWT_SECRET_KEY" ]; then
    echo ""
    echo "🔑 Registering JWT key in database..."
    
    if docker compose -f docker-compose.prod.yml exec -e JWT_SECRET_KEY="$JWT_SECRET_KEY" api python3 scripts/create-jwt-api-key.py; then
        echo ""
        echo "🎉 SUCCESS! JWT key registered successfully"
        
        # Test API authentication
        echo ""
        echo "🧪 Testing API authentication..."
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
        fi
        
    else
        echo ""
        echo "❌ JWT key registration failed"
        echo "Check container logs: docker compose -f docker-compose.prod.yml logs api"
    fi
else
    echo ""
    echo "⚠️ JWT_SECRET_KEY not provided. To complete setup:"
    echo "   export JWT_SECRET_KEY='your-jwt-key-from-github-secrets'"
    echo "   ./production-jwt-setup.sh"
fi

echo ""
echo "📋 Production JWT Setup Complete!"
#!/bin/bash

set -e

echo "🚀 Starting deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Clean up any existing containers to avoid port conflicts
echo "🧹 Cleaning up existing containers..."
docker compose -f docker-compose.prod.yml down --remove-orphans 2>/dev/null || echo "No existing containers to clean up"

# Function to safely load environment variables
load_env() {
    local env_file=$1
    if [ -f "$env_file" ]; then
        echo "Loading environment variables from $env_file..."
        # Remove comments, empty lines, and export safely
        while IFS= read -r line; do
            # Skip empty lines and comments
            [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
            # Remove inline comments and export
            clean_line=$(echo "$line" | sed 's/#.*//' | sed 's/[[:space:]]*$//')
            if [[ -n "$clean_line" ]]; then
                if ! export "$clean_line" 2>/dev/null; then
                    echo "Warning: Failed to export: $clean_line"
                fi
            fi
        done < "$env_file"
        echo "Environment variables loaded successfully"
    else
        echo "Warning: Environment file $env_file not found"
    fi
}

# Backup current configuration early to avoid rollback issues
echo "📦 Backing up current configuration..."
if [ -f ".env.prod" ]; then
    cp .env.prod .env.prod.backup
    echo "Backed up .env.prod"
else
    echo "No previous .env.prod to backup (first deployment)"
fi

if [ -f "docker-compose.prod.yml" ]; then
    cp docker-compose.prod.yml docker-compose.prod.yml.backup
    echo "Backed up docker-compose.prod.yml"
else
    echo "No previous docker-compose.prod.yml to backup"
fi

# Load environment variables (after backup, in case file was just created by CI)
load_env ".env.prod"

# Debug: Show that critical environment variables are loaded
echo "🔍 Verifying environment variables..."
echo "POSTGRES_USER: ${POSTGRES_USER:-NOT_SET}"
echo "POSTGRES_DB: ${POSTGRES_DB:-NOT_SET}"
echo "DATABASE_URL: ${DATABASE_URL:0:50}... (truncated for security)"
echo ""
echo "Redis Configuration:"
echo "REDIS_HOST: ${REDIS_HOST:-NOT_SET}"
echo "REDIS_PORT: ${REDIS_PORT:-NOT_SET}"
echo "REDIS_PASSWORD: ${REDIS_PASSWORD:+***SET***}${REDIS_PASSWORD:-NOT_SET}"
echo "REDIS_DB: ${REDIS_DB:-NOT_SET}"
echo "REDIS_URL: ${REDIS_URL:-NOT_SET}"

# Function to check if service is healthy
check_health() {
    local service=$1
    local max_attempts=30
    local attempt=1
    
    echo "Checking health of $service..."
    
    while [ $attempt -le $max_attempts ]; do
        if docker compose -f docker-compose.prod.yml ps $service | grep -q "healthy\|Up"; then
            echo -e "${GREEN}✅ $service is healthy${NC}"
            return 0
        fi
        
        echo "Attempt $attempt/$max_attempts: $service not ready yet..."
        sleep 10
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}❌ $service failed to become healthy${NC}"
    return 1
}

# Function to perform rollback
rollback() {
    echo -e "${YELLOW}⏪ Rolling back deployment...${NC}"
    
    # Get the previous successful deployment tag from backup
    if [ -f ".env.prod.backup" ]; then
        echo "Restoring previous configuration..."
        cp .env.prod.backup .env.prod
        load_env ".env.prod"
        
        # Restore docker compose file if backed up
        if [ -f "docker-compose.prod.yml.backup" ]; then
            cp docker-compose.prod.yml.backup docker-compose.prod.yml
        fi
        
        # Deploy previous version
        docker compose -f docker-compose.prod.yml up -d
        
        if check_health "api"; then
            echo -e "${GREEN}✅ Rollback successful${NC}"
            exit 0
        else
            echo -e "${RED}❌ Rollback failed${NC}"
            exit 1
        fi
    else
        echo -e "${YELLOW}⚠️  No backup found for rollback - this might be the first deployment${NC}"
        echo "Attempting to stop any running services..."
        docker compose -f docker-compose.prod.yml down 2>/dev/null || echo "No services to stop"
        echo -e "${YELLOW}⚠️  Rollback completed without restore${NC}"
        exit 1
    fi
}

# Trap to handle failures
trap rollback ERR

# Check if required environment variables are set
required_vars=("API_IMAGE_TAG" "WORKER_IMAGE_TAG" "POSTGRES_PASSWORD" "REDIS_PASSWORD")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo -e "${RED}❌ Required environment variable $var is not set${NC}"
        exit 1
    fi
done

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p ./logs ./data/postgres ./data/redis

# Stop services gracefully
echo "⏹️  Stopping current services..."
docker compose -f docker-compose.prod.yml down --timeout 30

# Clean up any orphaned containers
docker container prune -f

# Pull latest images
echo "📥 Pulling new images..."
docker compose -f docker-compose.prod.yml pull --parallel

# Start database and redis first
echo "🗄️  Starting database and cache services..."
docker compose -f docker-compose.prod.yml up -d db redis

# Wait for database and redis to be ready
echo "⏳ Waiting for database and redis..."
if ! check_health "db"; then
    echo -e "${RED}❌ Database failed to start${NC}"
    exit 1
fi

if ! check_health "redis"; then
    echo -e "${RED}❌ Redis failed to start${NC}"
    exit 1
fi

# Test database connection
echo "🔄 Testing database connection..."
if ! docker compose -f docker-compose.prod.yml exec -T db pg_isready -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
    echo -e "${RED}❌ Database connection failed${NC}"
    echo "Checking database logs..."
    docker compose -f docker-compose.prod.yml logs db --tail=20
    exit 1
fi
echo -e "${GREEN}✅ Database connection successful${NC}"

# Start application services
echo "🚀 Starting application services..."
docker compose -f docker-compose.prod.yml up -d api worker

# Wait for API to be ready
if ! check_health "api"; then
    echo -e "${RED}❌ API failed to start${NC}"
    exit 1
fi

# Start nginx (load balancer)
echo "🌐 Starting load balancer..."
docker compose -f docker-compose.prod.yml up -d nginx

if ! check_health "nginx"; then
    echo -e "${RED}❌ Load balancer failed to start${NC}"
    exit 1
fi

# Final health check with retries
echo "🏥 Performing final health check..."
echo "Waiting for application to fully initialize..."
sleep 30

# Health check with retries
max_health_attempts=10
health_attempt=1

echo "🔍 Testing health endpoints..."
while [ $health_attempt -le $max_health_attempts ]; do
    echo "Health check attempt $health_attempt/$max_health_attempts..."
    
    # Test nginx proxy health endpoint (only way to access API in production)
    if curl -f -m 10 http://localhost/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Application is healthy and responding via nginx proxy${NC}"
        break
    fi
    
    if [ $health_attempt -eq $max_health_attempts ]; then
        echo -e "${RED}❌ Application health check failed after $max_health_attempts attempts${NC}"
        echo "🔍 Debugging information:"
        echo "Container status:"
        docker compose -f docker-compose.prod.yml ps
        echo ""
        echo "API logs (last 30 lines):"
        docker compose -f docker-compose.prod.yml logs api --tail=30
        echo ""
        echo "Nginx logs (last 15 lines):"
        docker compose -f docker-compose.prod.yml logs nginx --tail=15
        echo ""
        echo "Network connectivity test:"
        echo "Testing nginx proxy (only exposed endpoint):"
        curl -v -m 5 http://localhost/health 2>&1 || echo "Nginx proxy connection failed"
        echo ""
        echo "Testing internal API health via docker exec:"
        docker compose -f docker-compose.prod.yml exec -T api curl -f http://localhost:8000/api/v1/health/live 2>&1 || echo "Internal API connection failed"
        exit 1
    fi
    
    echo "Waiting 15 seconds before next attempt..."
    sleep 15
    health_attempt=$((health_attempt + 1))
done

# Start monitoring if enabled
if docker compose -f docker-compose.prod.yml config --services | grep -q prometheus; then
    echo "📊 Starting monitoring services..."
    docker compose -f docker-compose.prod.yml up -d prometheus
fi

# Clean up old images and containers
echo "🧹 Cleaning up old resources..."
docker image prune -f
docker volume prune -f

# Remove backups on successful deployment
rm -f .env.prod.backup docker-compose.prod.yml.backup

echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo ""
echo "📋 Deployment Summary:"
echo "  • API Image: $API_IMAGE_TAG"
echo "  • Worker Image: $WORKER_IMAGE_TAG"
echo "  • Services running: $(docker compose -f docker-compose.prod.yml ps --services | tr '\n' ', ' | sed 's/,$//')"
echo ""
echo "🔍 Check status with: docker compose -f docker-compose.prod.yml ps"
echo "📝 Check logs with: docker compose -f docker-compose.prod.yml logs -f [service]"
#!/bin/bash

set -e

echo "🚀 Starting deployment..."

# Col        echo "Restoring previous configuration..."
        cp .env.prod.backup .env.prod
        load_env ".env.prod" for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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
            [[ -n "$clean_line" ]] && export "$clean_line"
        done < "$env_file"
    fi
}

# Load environment variables
load_env ".env.prod"

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
        export $(cat .env.prod | grep -v '^#' | grep -v '^\s*$' | sed 's/#.*//' | xargs)
        
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
        echo -e "${RED}❌ No backup found for rollback${NC}"
        exit 1
    fi
}

# Trap to handle failures
trap rollback ERR

# Backup current configuration
echo "📦 Backing up current configuration..."
cp .env.prod .env.prod.backup 2>/dev/null || echo "No previous .env.prod to backup"
cp docker-compose.prod.yml docker-compose.prod.yml.backup 2>/dev/null || echo "No previous compose file to backup"

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

# Run database migrations if needed
echo "🔄 Running database migrations..."
docker compose -f docker-compose.prod.yml exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1;" > /dev/null || {
    echo -e "${RED}❌ Database connection failed${NC}"
    exit 1
}

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

# Final health check
echo "🏥 Performing final health check..."
sleep 10

# Check API health endpoint
if curl -f -m 10 http://localhost/health > /dev/null 2>&1 || curl -f -m 10 http://localhost:8000/api/v1/health/live > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Application is healthy and responding${NC}"
else
    echo -e "${RED}❌ Application health check failed${NC}"
    exit 1
fi

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
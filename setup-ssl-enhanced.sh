#!/bin/bash

set -e

echo "🔧 Enhanced SSL Setup for AI Scraper..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

DOMAIN="paramita-scraper.duckdns.org"
EMAIL="your-email@example.com"  # Replace with your email
NGINX_CONF="./docker/nginx/nginx.conf"
DOCKER_COMPOSE="docker-compose.prod.yml"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

# Function to enable SSL in nginx.conf
enable_ssl_config() {
    echo -e "${BLUE}📝 Enabling SSL configuration in nginx.conf...${NC}"
    
    # Create backup
    cp "$NGINX_CONF" "$NGINX_CONF.backup"
    
    # Uncomment SSL server block
    sed -i 's/^    # HTTPS server (uncomment when SSL is configured)/    # HTTPS server (SSL configured)/' "$NGINX_CONF"
    sed -i 's/^    # server {/    server {/' "$NGINX_CONF"
    sed -i 's/^    #     listen 443 ssl;/        listen 443 ssl;/' "$NGINX_CONF"
    sed -i 's/^    #     http2 on;/        http2 on;/' "$NGINX_CONF"
    sed -i 's/^    #     server_name paramita-scraper.duckdns.org;/        server_name paramita-scraper.duckdns.org;/' "$NGINX_CONF"
    
    # Uncomment SSL certificate lines
    sed -i 's/^    #     ssl_certificate /        ssl_certificate /' "$NGINX_CONF"
    sed -i 's/^    #     ssl_certificate_key /        ssl_certificate_key /' "$NGINX_CONF"
    
    # Uncomment SSL configuration and location blocks  
    sed -i 's/^    #     /        /' "$NGINX_CONF"
    sed -i 's/^    # }/    }/' "$NGINX_CONF"
    
    echo -e "${GREEN}✅ SSL configuration enabled${NC}"
}

# Function to add SSL volume mount to docker-compose
enable_ssl_volume() {
    echo -e "${BLUE}📝 Adding SSL volume mount to docker-compose...${NC}"
    
    # Create backup
    cp "$DOCKER_COMPOSE" "$DOCKER_COMPOSE.backup"
    
    # Uncomment SSL volume mount
    if grep -q "# - /etc/letsencrypt:/etc/letsencrypt:ro" "$DOCKER_COMPOSE"; then
        sed -i 's/# - \/etc\/letsencrypt:\/etc\/letsencrypt:ro/      - \/etc\/letsencrypt:\/etc\/letsencrypt:ro/' "$DOCKER_COMPOSE"
        echo -e "${GREEN}✅ SSL volume mount enabled${NC}"
    elif ! grep -q "/etc/letsencrypt:/etc/letsencrypt:ro" "$DOCKER_COMPOSE"; then
        sed -i '/scraper_prod_logs:\/var\/log\/nginx/a\      - /etc/letsencrypt:/etc/letsencrypt:ro' "$DOCKER_COMPOSE"
        echo -e "${GREEN}✅ SSL volume mount added${NC}"
    else
        echo -e "${YELLOW}⚠️  SSL volume mount already present${NC}"
    fi
}

# Install certbot if not already installed
if ! command -v certbot &> /dev/null; then
    echo -e "${BLUE}📦 Installing certbot...${NC}"
    if command -v apt-get &> /dev/null; then
        apt-get update
        apt-get install -y certbot
    elif command -v yum &> /dev/null; then
        yum install -y certbot
    else
        echo -e "${RED}Please install certbot manually${NC}"
        exit 1
    fi
fi

# Stop nginx temporarily to allow certbot to bind to port 80
echo -e "${YELLOW}🛑 Temporarily stopping nginx...${NC}"
docker compose -f "$DOCKER_COMPOSE" stop nginx 2>/dev/null || echo "Nginx not running"

# Create SSL certificate
echo -e "${BLUE}🔐 Obtaining SSL certificate for $DOMAIN...${NC}"
certbot certonly \
    --standalone \
    --non-interactive \
    --agree-tos \
    --email "$EMAIL" \
    -d "$DOMAIN" \
    --force-renewal

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ SSL certificate obtained successfully!${NC}"
    
    # Set proper permissions
    chmod -R 755 /etc/letsencrypt
    
    # Enable SSL configuration
    enable_ssl_config
    enable_ssl_volume
    
    # Restart services with SSL enabled
    echo -e "${BLUE}🚀 Restarting services with SSL...${NC}"
    docker compose -f "$DOCKER_COMPOSE" up -d --build
    
    # Wait for services to start
    echo -e "${BLUE}⏳ Waiting for services to be ready...${NC}"
    sleep 15
    
    # Test SSL
    echo -e "${BLUE}🧪 Testing SSL connection...${NC}"
    sleep 5
    
    # Test HTTP first
    if curl -sf http://"$DOMAIN"/health > /dev/null; then
        echo -e "${GREEN}✅ HTTP is working!${NC}"
    else
        echo -e "${YELLOW}⚠️  HTTP may need a few moments...${NC}"
    fi
    
    # Test HTTPS
    if curl -sf https://"$DOMAIN"/health > /dev/null; then
        echo -e "${GREEN}✅ HTTPS is working!${NC}"
    else
        echo -e "${YELLOW}⚠️  HTTPS may need a few moments to be ready${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}🎉 SSL Setup Complete!${NC}"
    echo "📋 SSL Certificate Information:"
    echo "Domain: $DOMAIN"
    echo "Certificate: /etc/letsencrypt/live/$DOMAIN/fullchain.pem"
    echo "Private Key: /etc/letsencrypt/live/$DOMAIN/privkey.pem"
    echo ""
    echo "🌐 Your API is now available at:"
    echo "  HTTP:  http://$DOMAIN/api/v1"
    echo "  HTTPS: https://$DOMAIN/api/v1"
    echo ""
    echo "🔄 Certificate will auto-renew. To renew manually: certbot renew"
    
else
    echo -e "${RED}❌ Failed to obtain SSL certificate${NC}"
    echo -e "${YELLOW}🔄 Restoring configuration and restarting without SSL...${NC}"
    
    # Restore backups if they exist
    if [ -f "$NGINX_CONF.backup" ]; then
        mv "$NGINX_CONF.backup" "$NGINX_CONF"
    fi
    if [ -f "$DOCKER_COMPOSE.backup" ]; then
        mv "$DOCKER_COMPOSE.backup" "$DOCKER_COMPOSE"
    fi
    
    docker compose -f "$DOCKER_COMPOSE" up -d
    exit 1
fi
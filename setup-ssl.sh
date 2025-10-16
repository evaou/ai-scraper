#!/bin/bash

set -e

echo "🔒 Setting up SSL certificates for paramita-scraper.duckdns.org..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

DOMAIN="paramita-scraper.duckdns.org"
EMAIL="your-email@example.com"  # Replace with your email

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

# Install certbot if not already installed
if ! command -v certbot &> /dev/null; then
    echo "📦 Installing certbot..."
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
echo "🛑 Temporarily stopping nginx..."
docker compose -f docker-compose.prod.yml stop nginx 2>/dev/null || echo "Nginx not running"

# Create SSL certificate
echo "🔐 Obtaining SSL certificate for $DOMAIN..."
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
    
    # Restart nginx with SSL enabled
    echo "🚀 Restarting services with SSL..."
    docker compose -f docker-compose.prod.yml up -d
    
    # Test SSL
    echo "🧪 Testing SSL connection..."
    sleep 10
    if curl -sI https://"$DOMAIN"/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ HTTPS is working!${NC}"
        echo "🌐 Your API is now available at: https://$DOMAIN"
    else
        echo -e "${YELLOW}⚠️  SSL certificate installed, but HTTPS may need a few moments to be ready${NC}"
    fi
    
    echo ""
    echo "📋 SSL Certificate Information:"
    echo "Domain: $DOMAIN"
    echo "Certificate: /etc/letsencrypt/live/$DOMAIN/fullchain.pem"
    echo "Private Key: /etc/letsencrypt/live/$DOMAIN/privkey.pem"
    echo ""
    echo "🔄 Certificate will auto-renew. To renew manually: certbot renew"
    
else
    echo -e "${RED}❌ Failed to obtain SSL certificate${NC}"
    echo "Restarting nginx without SSL..."
    docker compose -f docker-compose.prod.yml up -d
    exit 1
fi
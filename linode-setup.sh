#!/bin/bash

# Linode Server Setup Script
# Run this on your Linode server after initial creation

set -e

echo "🚀 Setting up Linode server for AI Scraper deployment..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
echo "📦 Installing Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Docker Compose is now built into Docker
echo "📦 Docker Compose is included with Docker (using 'docker compose')"

# Create application directory
sudo mkdir -p /opt/ai-scraper
sudo chown $USER:$USER /opt/ai-scraper

# Install useful tools
sudo apt install -y curl wget git htop nano

# Test Docker Compose V2
echo "🧪 Testing Docker Compose V2..."
if docker compose version > /dev/null 2>&1; then
    echo "✅ Docker Compose V2 is working"
else
    echo "❌ Docker Compose V2 not available, installing plugin..."
    mkdir -p ~/.docker/cli-plugins/
    curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 -o ~/.docker/cli-plugins/docker-compose
    chmod +x ~/.docker/cli-plugins/docker-compose
fi

echo "✅ Linode server setup complete!"
echo ""
echo "Next steps:"
echo "1. Log out and back in to apply Docker group changes"
echo "2. Test Docker: docker run hello-world"
echo "3. Test Docker Compose: docker compose version"
echo "4. Set up SSH keys for GitHub Actions"

# Display server info
echo ""
echo "Server Information:"
echo "  IP Address: $(curl -s ifconfig.me)"
echo "  OS: $(lsb_release -d | cut -f2)"
echo "  Docker: $(docker --version)"
echo "  Docker Compose: $(docker compose version)"

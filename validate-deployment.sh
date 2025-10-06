#!/bin/bash

# Deployment Validation Script
# Validates that the server is ready for docker compose deployment

set -e

echo "🔍 Validating deployment environment..."
echo "======================================"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check command availability
check_command() {
    local cmd=$1
    local description=$2
    
    if command -v $cmd > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $description: Available${NC}"
        return 0
    else
        echo -e "${RED}❌ $description: Not found${NC}"
        return 1
    fi
}

# Function to check docker compose specifically
check_docker_compose() {
    if docker compose version > /dev/null 2>&1; then
        local version=$(docker compose version --short)
        echo -e "${GREEN}✅ Docker Compose V2: $version${NC}"
        return 0
    else
        echo -e "${RED}❌ Docker Compose V2: Not available${NC}"
        echo -e "${YELLOW}💡 Install with: mkdir -p ~/.docker/cli-plugins/ && curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 -o ~/.docker/cli-plugins/docker-compose && chmod +x ~/.docker/cli-plugins/docker-compose${NC}"
        return 1
    fi
}

echo ""
echo "📦 Checking required software:"
echo "-----------------------------"

# Check Docker
check_command "docker" "Docker"

# Check Docker Compose V2
check_docker_compose

# Check other tools
check_command "curl" "curl"
check_command "git" "git"

echo ""
echo "📂 Checking directory structure:"
echo "-------------------------------"

# Check if deployment directory exists
if [ -d "/opt/ai-scraper" ]; then
    echo -e "${GREEN}✅ Deployment directory: /opt/ai-scraper exists${NC}"
    
    # Check permissions
    if [ -w "/opt/ai-scraper" ]; then
        echo -e "${GREEN}✅ Directory permissions: Writable${NC}"
    else
        echo -e "${RED}❌ Directory permissions: Not writable${NC}"
    fi
    
    # List contents
    echo "📋 Current contents:"
    ls -la /opt/ai-scraper/ 2>/dev/null || echo "  (empty or no access)"
else
    echo -e "${YELLOW}⚠️ Deployment directory: /opt/ai-scraper does not exist${NC}"
    echo -e "${YELLOW}💡 Create with: sudo mkdir -p /opt/ai-scraper && sudo chown \$USER:\$USER /opt/ai-scraper${NC}"
fi

echo ""
echo "🔐 Checking SSH configuration:"
echo "-----------------------------"

# Check SSH key
if [ -f "$HOME/.ssh/authorized_keys" ]; then
    echo -e "${GREEN}✅ SSH authorized_keys: Exists${NC}"
    
    # Check for GitHub Actions key
    if grep -q "github-actions-ai-scraper" "$HOME/.ssh/authorized_keys" 2>/dev/null; then
        echo -e "${GREEN}✅ GitHub Actions SSH key: Found${NC}"
    else
        echo -e "${YELLOW}⚠️ GitHub Actions SSH key: Not found${NC}"
        echo -e "${YELLOW}💡 Add with: echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINAyLXMQfx5k/+DgaQrcfDVqosS3sTBbatsngjXHHZez github-actions-ai-scraper' >> ~/.ssh/authorized_keys${NC}"
    fi
else
    echo -e "${RED}❌ SSH authorized_keys: Not found${NC}"
    echo -e "${YELLOW}💡 Create with: mkdir -p ~/.ssh && touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys${NC}"
fi

echo ""
echo "🌐 Checking network connectivity:"
echo "--------------------------------"

# Check internet connectivity
if curl -s --connect-timeout 5 https://github.com > /dev/null; then
    echo -e "${GREEN}✅ Internet connectivity: Working${NC}"
else
    echo -e "${RED}❌ Internet connectivity: Failed${NC}"
fi

# Check GitHub Container Registry access
if curl -s --connect-timeout 5 https://ghcr.io > /dev/null; then
    echo -e "${GREEN}✅ GitHub Container Registry: Accessible${NC}"
else
    echo -e "${RED}❌ GitHub Container Registry: Not accessible${NC}"
fi

echo ""
echo "🐳 Testing Docker functionality:"
echo "-------------------------------"

# Test Docker daemon
if docker info > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Docker daemon: Running${NC}"
else
    echo -e "${RED}❌ Docker daemon: Not running${NC}"
fi

# Test Docker Compose with a simple test
if docker compose version > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Docker Compose: Functional${NC}"
    
    # Create a test compose file
    cat > /tmp/test-compose.yml << 'EOF'
version: '3.8'
services:
  test:
    image: hello-world
EOF
    
    # Test compose functionality
    if docker compose -f /tmp/test-compose.yml config > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Docker Compose config validation: Working${NC}"
    else
        echo -e "${RED}❌ Docker Compose config validation: Failed${NC}"
    fi
    
    # Clean up test file
    rm -f /tmp/test-compose.yml
else
    echo -e "${RED}❌ Docker Compose: Not functional${NC}"
fi

echo ""
echo "📊 System Resources:"
echo "-------------------"

# Check available disk space
available_space=$(df -h / | awk 'NR==2 {print $4}')
echo "💾 Available disk space: $available_space"

# Check available memory
if command -v free > /dev/null 2>&1; then
    available_memory=$(free -h | awk 'NR==2 {print $7}')
    echo "🧠 Available memory: $available_memory"
fi

# Check CPU cores
cpu_cores=$(nproc 2>/dev/null || echo "unknown")
echo "⚙️ CPU cores: $cpu_cores"

echo ""
echo "======================================"
echo "🎯 Deployment Readiness Summary:"
echo "======================================"

# Count successful checks (simplified)
checks_passed=0
total_checks=8

# Basic readiness check
if command -v docker > /dev/null 2>&1 && docker compose version > /dev/null 2>&1 && [ -d "/opt/ai-scraper" ]; then
    echo -e "${GREEN}✅ Server is ready for Docker Compose deployment!${NC}"
    echo ""
    echo "🚀 To deploy:"
    echo "1. Configure GitHub secrets (see DEPLOYMENT_SETUP.md)"
    echo "2. Push to main branch or trigger workflow manually"
    echo "3. Monitor deployment at: GitHub → Actions → Deploy to Linode"
else
    echo -e "${RED}❌ Server needs additional setup before deployment${NC}"
    echo ""
    echo "🔧 Required actions:"
    [ ! -command -v docker ] && echo "  • Install Docker"
    ! docker compose version > /dev/null 2>&1 && echo "  • Install Docker Compose V2"
    [ ! -d "/opt/ai-scraper" ] && echo "  • Create deployment directory"
    echo ""
    echo "💡 Run the linode-setup.sh script to fix these issues"
fi

echo ""
echo "📚 Documentation:"
echo "  • Setup Guide: DEPLOYMENT_SETUP.md"
echo "  • Troubleshooting: Check GitHub Actions logs"
echo "  • Monitor: docker compose -f docker-compose.prod.yml logs -f"
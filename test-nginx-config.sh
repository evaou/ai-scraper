#!/bin/bash

# Quick nginx configuration test
# This validates nginx.conf before deployment

echo "🔍 Testing nginx configuration..."

# Test nginx config syntax using docker
if docker run --rm -v "$(pwd)/docker/nginx/nginx.conf:/etc/nginx/nginx.conf:ro" nginx:alpine nginx -t 2>/dev/null; then
    echo "✅ Nginx configuration is valid"
    exit 0
else
    echo "❌ Nginx configuration has errors:"
    docker run --rm -v "$(pwd)/docker/nginx/nginx.conf:/etc/nginx/nginx.conf:ro" nginx:alpine nginx -t
    exit 1
fi
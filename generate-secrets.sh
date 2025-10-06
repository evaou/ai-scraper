#!/bin/bash

# Generate Secure Secrets for GitHub Actions Deployment
# Run this locally to generate all required passwords

echo "🔐 Generating secure secrets for GitHub Actions deployment..."
echo "======================================================"
echo ""

echo "📋 Copy these values to GitHub Secrets:"
echo ""

echo "Server Connection Secrets:"
echo "-------------------------"
echo "LINODE_HOST: YOUR_LINODE_SERVER_IP"
echo "LINODE_USER: root"
echo "SSH_PRIVATE_KEY: [Copy the private key from the setup guide]"
echo ""

echo "Database Secrets:"
echo "----------------"
POSTGRES_PASSWORD=$(openssl rand -base64 16)
echo "POSTGRES_DB: scraper_prod"
echo "POSTGRES_USER: scraper_user"
echo "POSTGRES_PASSWORD: $POSTGRES_PASSWORD"
echo ""

echo "Cache Secrets:"
echo "-------------"
REDIS_PASSWORD=$(openssl rand -base64 16)
echo "REDIS_PASSWORD: $REDIS_PASSWORD"
echo ""

echo "Security Secrets:"
echo "----------------"
JWT_SECRET=$(openssl rand -base64 32)
echo "JWT_SECRET_KEY: $JWT_SECRET"
echo ""

echo "======================================================"
echo "✅ All secrets generated!"
echo ""
echo "Next steps:"
echo "1. Go to GitHub → Your repo → Settings → Secrets and variables → Actions"
echo "2. Add each secret with 'New repository secret'"
echo "3. Use the exact secret names shown above"
echo "4. Replace YOUR_LINODE_SERVER_IP with your actual server IP"
echo ""
echo "🚀 After adding all secrets, push to main branch or manually trigger the workflow!"
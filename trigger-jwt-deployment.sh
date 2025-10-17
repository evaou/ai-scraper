#!/bin/bash

# Alternative: Trigger Automatic JWT Registration via Deployment
# This script pushes a commit to trigger the deployment workflow
# which will automatically register the JWT key

echo "🚀 AI Scraper - Automatic JWT Registration via Deployment"
echo "========================================================="
echo ""

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ ERROR: Not in a git repository"
    exit 1
fi

# Check if we have uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "⚠️ You have uncommitted changes. Commit them first or stash them."
    echo ""
    echo "Current changes:"
    git status --porcelain
    echo ""
    echo "Options:"
    echo "1. Commit changes: git add . && git commit -m 'Your message'"
    echo "2. Stash changes: git stash"
    exit 1
fi

# Get current branch
CURRENT_BRANCH=$(git branch --show-current)

if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "⚠️ You are on branch '$CURRENT_BRANCH', not 'main'"
    echo ""
    echo "Options:"
    echo "1. Switch to main: git checkout main && git pull"
    echo "2. Continue with current branch (will deploy from this branch)"
    echo ""
    read -p "Continue with '$CURRENT_BRANCH'? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled. Switch to main branch first."
        exit 1
    fi
fi

# Create a commit to trigger deployment
echo "📝 Creating deployment trigger commit..."

# Add a timestamp to force deployment
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
echo "# Deployment triggered at $TIMESTAMP" >> .deployment-trigger

git add .deployment-trigger
git commit -m "Trigger deployment for JWT key registration - $TIMESTAMP"

echo "✅ Commit created"

# Push to trigger deployment
echo ""
echo "🚀 Pushing to trigger deployment workflow..."

if git push origin "$CURRENT_BRANCH"; then
    echo ""
    echo "🎉 SUCCESS! Deployment triggered."
    echo ""
    echo "📋 What happens next:"
    echo "1. GitHub Actions will run the deployment workflow"
    echo "2. The workflow will automatically register the JWT_SECRET_KEY"
    echo "3. Your containers will restart with the new configuration"
    echo "4. Both workflows will use enhanced API mode"
    echo ""
    echo "🔍 Monitor progress:"
    echo "• GitHub Actions: https://github.com/$(git config remote.origin.url | sed 's/.*github.com[:/]\(.*\)\.git.*/\1/')/actions"
    echo "• Check deployment: ssh to your server and run 'docker compose -f docker-compose.prod.yml ps'"
    echo ""
    echo "⏱️ Deployment usually takes 5-10 minutes"
    
    # Clean up the trigger file
    git rm .deployment-trigger
    git commit -m "Clean up deployment trigger file"
    git push origin "$CURRENT_BRANCH"
    
else
    echo ""
    echo "❌ Failed to push. Check your git configuration and permissions."
    exit 1
fi

echo ""
echo "📋 Automatic Deployment Trigger Complete!"
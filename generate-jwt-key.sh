#!/bin/bash

# Quick JWT Key Generator
# Use this to generate a new JWT_SECRET_KEY for GitHub repository secrets

echo "🔑 JWT_SECRET_KEY Generator"
echo "=========================="
echo ""

# Generate a new JWT secret key
NEW_JWT_KEY=$(openssl rand -base64 32)

echo "✅ New JWT_SECRET_KEY generated:"
echo ""
echo "🔐 JWT_SECRET_KEY:"
echo "$NEW_JWT_KEY"
echo ""
echo "📋 SETUP INSTRUCTIONS:"
echo ""
echo "1️⃣ Copy the JWT key above"
echo ""
echo "2️⃣ Add it to GitHub repository secrets:"
echo "   • Go to: GitHub Repository → Settings → Secrets and variables → Actions"
echo "   • Click: 'New repository secret'"
echo "   • Name: JWT_SECRET_KEY"
echo "   • Value: $NEW_JWT_KEY"
echo "   • Click: 'Add secret'"
echo ""
echo "3️⃣ Register the key on your production server:"
echo "   export JWT_SECRET_KEY='$NEW_JWT_KEY'"
echo "   ./manual-jwt-registration.sh"
echo ""
echo "4️⃣ Test your workflows:"
echo "   • Trigger 'Email USD Spot Selling Rate' workflow"
echo "   • Trigger 'Stock Price Alert Email' workflow"
echo "   • Both should now use 'Enhanced API mode'"
echo ""
echo "💡 TIP: Keep this key secure and only use it in GitHub secrets and production server"
echo ""
echo "✅ JWT Key Generation Complete!"
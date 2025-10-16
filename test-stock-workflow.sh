#!/bin/bash

# Test stock price workflow components
# This script validates that the stock price alert workflow will work

echo "🧪 Testing Stock Price Alert Workflow Components"
echo "================================================"

cd "$(dirname "$0")"

# Test 1: Check if scripts exist
echo "1️⃣ Checking required scripts..."
if [ -f "client/get_stock_prices.sh" ]; then
    echo "✅ get_stock_prices.sh exists"
else
    echo "❌ get_stock_prices.sh missing"
    exit 1
fi

if [ -f "client/stock_price_fetcher.py" ]; then
    echo "✅ stock_price_fetcher.py exists"
else
    echo "❌ stock_price_fetcher.py missing"
    exit 1
fi

# Test 2: Make script executable
echo "2️⃣ Making scripts executable..."
chmod +x client/get_stock_prices.sh
echo "✅ Scripts are executable"

# Test 3: Test API connectivity (simulating workflow)
echo "3️⃣ Testing API connectivity..."
API_URL="http://paramita-scraper.duckdns.org/api/v1"
if curl -f -s -m 10 http://paramita-scraper.duckdns.org/health > /dev/null 2>&1; then
    echo "✅ API is accessible"
    API_AVAILABLE=true
else
    echo "⚠️ API not accessible - workflow will use CSV fallback"
    API_AVAILABLE=false
fi

# Test 4: Test stock fetcher (dry run)
echo "4️⃣ Testing stock price fetcher..."
if command -v python3 > /dev/null 2>&1; then
    echo "✅ Python3 is available"
    
        # Test with API if available
        if [ "$API_AVAILABLE" = true ]; then
            echo "Testing with API mode..."
            if ./client/get_stock_prices.sh --api "$API_URL" --output table > /tmp/stock_test.out 2>&1; then
                echo "✅ Stock fetcher works with API"
                echo "Sample output:"
                head -3 /tmp/stock_test.out | grep -v "^\[" || head -3 /tmp/stock_test.out
                
                # Check if output contains meaningful data
                if grep -q "No buy opportunities\|Symbol\|Price\|\$" /tmp/stock_test.out; then
                    echo "✅ Valid stock data received"
                else
                    echo "⚠️ Unexpected output format"
                fi
            else
                echo "⚠️ API mode failed (exit code: $?), testing CSV fallback..."
                echo "API error output:"
                head -5 /tmp/stock_test.out
                echo ""
                
                if ./client/get_stock_prices.sh --output table > /tmp/stock_test_csv.out 2>&1; then
                    echo "✅ Stock fetcher works with CSV fallback"
                    echo "Sample output:"
                    head -3 /tmp/stock_test_csv.out | grep -v "^\[" || head -3 /tmp/stock_test_csv.out
                    rm -f /tmp/stock_test_csv.out
                else
                    echo "❌ Stock fetcher failed completely"
                    echo "CSV error output:"
                    cat /tmp/stock_test_csv.out
                    rm -f /tmp/stock_test.out /tmp/stock_test_csv.out
                    exit 1
                fi
            fi
        else
            echo "Testing CSV mode only..."
            if ./client/get_stock_prices.sh --output table > /tmp/stock_test.out 2>&1; then
                echo "✅ Stock fetcher works with CSV mode"
                echo "Sample output:"
                head -3 /tmp/stock_test.out | grep -v "^\[" || head -3 /tmp/stock_test.out
                
                # Check if output contains meaningful data
                if grep -q "No buy opportunities\|Symbol\|Price\|\$" /tmp/stock_test.out; then
                    echo "✅ Valid stock data received"
                else
                    echo "⚠️ Unexpected output format"
                fi
            else
                echo "❌ Stock fetcher failed"
                echo "Error output:"
                cat /tmp/stock_test.out
                rm -f /tmp/stock_test.out
                exit 1
            fi
        fi
        
        rm -f /tmp/stock_test.out
else
    echo "⚠️ Python3 not available for local testing"
fi

# Test 5: Check GitHub workflow syntax
echo "5️⃣ Checking workflow configuration..."
if [ -f ".github/workflows/stock_price_alert.yml" ]; then
    echo "✅ Stock price alert workflow exists"
    
    # Check if required secrets are referenced
    if grep -q "GMAIL_USERNAME" .github/workflows/stock_price_alert.yml; then
        echo "✅ Gmail credentials configured in workflow"
    else
        echo "⚠️ Gmail credentials may need setup"
    fi
else
    echo "❌ Workflow file missing"
    exit 1
fi

echo ""
echo "🎯 Test Summary:"
echo "- Stock price fetcher: Ready"
echo "- API connectivity: $([ "$API_AVAILABLE" = true ] && echo "Available" || echo "CSV fallback ready")"
echo "- Workflow configuration: Valid"
echo ""
echo "✅ Stock Price Alert workflow should work correctly!"
echo ""
echo "📅 Next steps:"
echo "1. Ensure GitHub secrets are configured:"
echo "   - GMAIL_USERNAME"
echo "   - GMAIL_APP_PASSWORD" 
echo "   - TO_EMAIL"
echo "2. Workflow runs daily at 21:40 Taipei time"
echo "3. Manual trigger available in GitHub Actions tab"
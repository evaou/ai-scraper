#!/bin/bash

# USD Rate Checker Script
# Simple script to check current USD selling rate from Bank of Taiwan

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRAPER_SCRIPT="$SCRIPT_DIR/usd_rate_scraper.py"
URL="https://rate.bot.com.tw/xrt?Lang=en-US"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python script exists
if [ ! -f "$SCRAPER_SCRIPT" ]; then
    print_error "USD Rate Scraper not found at: $SCRAPER_SCRIPT"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed"
    exit 1
fi

print_status "Fetching current USD selling rate from Bank of Taiwan..."

# Get the rate
if RATE=$(python3 "$SCRAPER_SCRIPT" --url "$URL" --manual-fallback --quiet 2>/dev/null); then
    print_success "Current USD Selling Rate: $RATE TWD"
    
    # Rate analysis (using bc for floating point comparison)
    if command -v bc &> /dev/null; then
        if (( $(echo "$RATE < 30.0" | bc -l) )); then
            print_success "🟢 Excellent rate for selling USD!"
        elif (( $(echo "$RATE < 30.5" | bc -l) )); then
            print_success "🟡 Good rate for selling USD"
        elif (( $(echo "$RATE < 31.0" | bc -l) )); then
            print_warning "🟠 Average rate"
        else
            print_warning "🔴 Rate is relatively high"
        fi
        
        echo
        echo "Rate Guidelines:"
        echo "  • < 30.0: Excellent for USD sellers"
        echo "  • 30.0-30.5: Good rate"
        echo "  • 30.5-31.0: Average rate"
        echo "  • > 31.0: Consider waiting"
    else
        print_warning "Install 'bc' for rate analysis features"
    fi
    
    # Timestamp
    echo
    echo "Last updated: $(date)"
    
else
    print_error "Failed to fetch USD rate"
    print_status "Try running with verbose mode for debugging:"
    echo "  python3 $SCRAPER_SCRIPT --url \"$URL\" --manual-fallback --verbose"
    exit 1
fi
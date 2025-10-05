#!/usr/bin/env python3
"""
USD Rate Scraper - Example Usage

This script demonstrates how to use the USD rate scraper programmatically
within other Python applications.

Author: AI Scraper
Date: 2025-10-04
"""

import subprocess
import json
import sys
from decimal import Decimal
from pathlib import Path

# Configuration
SCRAPER_PATH = Path(__file__).parent / "usd_rate_scraper.py"
BANK_URL = "https://rate.bot.com.tw/xrt?Lang=en-US"


def get_usd_rate() -> Decimal:
    """
    Get current USD selling rate from Bank of Taiwan.
    
    Returns:
        Current USD selling rate as Decimal
        
    Raises:
        subprocess.CalledProcessError: If scraper fails
        ValueError: If rate cannot be parsed
    """
    try:
        result = subprocess.run([
            "python3", str(SCRAPER_PATH),
            "--url", BANK_URL,
            "--manual-fallback",
            "--quiet"
        ], capture_output=True, text=True, check=True)
        
        rate_str = result.stdout.strip()
        return Decimal(rate_str)
        
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to get USD rate: {e.stderr}")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid rate format: {result.stdout.strip()}")


def analyze_rate(rate: Decimal) -> dict:
    """
    Analyze USD rate and provide recommendations.
    
    Args:
        rate: USD selling rate
        
    Returns:
        Dictionary with analysis results
    """
    analysis = {
        "rate": float(rate),
        "currency_pair": "USD/TWD",
        "timestamp": None,  # Would need to be added by scraper
        "recommendation": None,
        "category": None,
        "color": None
    }
    
    if rate < Decimal('30.0'):
        analysis.update({
            "recommendation": "Excellent time to sell USD",
            "category": "excellent",
            "color": "green"
        })
    elif rate < Decimal('30.5'):
        analysis.update({
            "recommendation": "Good time to sell USD", 
            "category": "good",
            "color": "yellow"
        })
    elif rate < Decimal('31.0'):
        analysis.update({
            "recommendation": "Average rate - consider timing",
            "category": "average", 
            "color": "orange"
        })
    else:
        analysis.update({
            "recommendation": "Consider waiting for better rate",
            "category": "high",
            "color": "red"
        })
    
    return analysis


def send_rate_alert(email: str, threshold: float = 30.5) -> bool:
    """
    Send email alert if rate is below threshold.
    
    Args:
        email: Target email address
        threshold: Rate threshold for alert
        
    Returns:
        True if alert sent successfully, False otherwise
    """
    try:
        subprocess.run([
            "python3", str(SCRAPER_PATH),
            "--url", BANK_URL,
            "--manual-fallback", 
            "--quiet",
            "--email", email,
            "--threshold", str(threshold),
            # Note: This would need SMTP settings to actually work
        ], check=True, capture_output=True)
        return True
        
    except subprocess.CalledProcessError:
        return False


def main():
    """Main example function."""
    print("🏦 USD Rate Scraper - Python Example")
    print("=" * 40)
    
    try:
        # Get current rate
        print("📊 Fetching current USD selling rate...")
        rate = get_usd_rate()
        print(f"✅ Current Rate: {rate} TWD per USD")
        
        # Analyze the rate
        print("\n📈 Rate Analysis:")
        analysis = analyze_rate(rate)
        
        print(f"   Rate: {analysis['rate']} TWD")
        print(f"   Category: {analysis['category'].upper()}")
        print(f"   Recommendation: {analysis['recommendation']}")
        
        # Example: Rate comparison
        print("\n📋 Rate Guidelines:")
        guidelines = [
            ("< 30.0", "Excellent for USD sellers", "🟢"),
            ("30.0-30.5", "Good rate", "🟡"),
            ("30.5-31.0", "Average rate", "🟠"),
            ("> 31.0", "Consider waiting", "🔴")
        ]
        
        for range_text, desc, emoji in guidelines:
            print(f"   {emoji} {range_text}: {desc}")
        
        # Example: Programmatic decision making
        print("\n🤖 Programmatic Decision:")
        if analysis['category'] == 'excellent':
            print("   → Trigger: SELL USD NOW")
        elif analysis['category'] == 'good':
            print("   → Trigger: Good time to sell")
        elif analysis['category'] == 'average':
            print("   → Trigger: Monitor rate changes")
        else:
            print("   → Trigger: Wait for better rate")
        
        # Example: JSON output for API integration
        print(f"\n📄 JSON Output:")
        print(json.dumps(analysis, indent=2))
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
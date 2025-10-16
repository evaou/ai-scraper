#!/usr/bin/env python3
"""
Simple script to create an API key for the AI Scraper service.

This script connects to the database and creates an API key that can be used
by GitHub Actions workflows to access the API without fallback.

Usage:
    python3 scripts/create-api-key.py --name "GitHub Actions" --description "API key for workflows"
    
Environment Variables:
    DATABASE_URL: PostgreSQL connection URL (defaults to production settings)
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.api_key import ApiKey


async def create_api_key(name: str, description: str = None) -> tuple[str, str]:
    """Create an API key and return the key and prefix."""
    
    # Database URL - use production settings
    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://scraper_user:password@localhost:5432/scraper_prod")
    
    # Create engine and session
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            # Create API key
            api_key, raw_key = ApiKey.create_api_key(
                name=name,
                description=description,
                rate_limit_per_minute=200,  # Higher limits for workflow usage
                rate_limit_per_hour=2000,
                rate_limit_per_day=20000,
            )
            
            # Add to database
            session.add(api_key)
            await session.commit()
            
            return raw_key, api_key.key_prefix
            
    finally:
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="Create an API key for AI Scraper")
    parser.add_argument("--name", required=True, help="Name for the API key")
    parser.add_argument("--description", help="Description for the API key")
    
    args = parser.parse_args()
    
    try:
        raw_key, key_prefix = asyncio.run(create_api_key(args.name, args.description))
        
        print("✅ API Key created successfully!")
        print(f"📋 Name: {args.name}")
        print(f"🔑 Key: {raw_key}")
        print(f"🏷️  Prefix: {key_prefix}")
        print("")
        print("🚨 IMPORTANT: Save this key securely! It cannot be retrieved again.")
        print("")
        print("📝 To use in GitHub Actions, add this as a secret named 'AI_SCRAPER_API_KEY'")
        print("   Go to: Repository Settings → Secrets and Variables → Actions → New secret")
        
    except Exception as e:
        print(f"❌ Error creating API key: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
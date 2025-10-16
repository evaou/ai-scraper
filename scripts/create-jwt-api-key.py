#!/usr/bin/env python3
"""
Create an API key using the JWT_SECRET_KEY value.

This script creates an API key in the database using the JWT_SECRET_KEY as the raw key value,
so that GitHub Actions workflows can use the existing JWT_SECRET_KEY secret for API authentication.

Usage:
    python3 scripts/create-jwt-api-key.py
    
Environment Variables:
    DATABASE_URL: PostgreSQL connection URL (defaults to production settings)
    JWT_SECRET_KEY: The JWT secret to use as the API key
"""

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


async def create_jwt_api_key() -> tuple[str, str]:
    """Create an API key using JWT_SECRET_KEY and return the key and prefix."""
    
    # Get JWT secret key
    jwt_secret = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
    
    if not jwt_secret or jwt_secret == "dev-secret-key-change-in-production":
        print("⚠️ Warning: Using default JWT_SECRET_KEY. In production, ensure JWT_SECRET_KEY is properly set.")
    
    # Database URL - use production settings
    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://scraper_user:password@localhost:5432/scraper_prod")
    
    # Create engine and session
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            # Check if an API key with this hash already exists
            key_hash = ApiKey.hash_key(jwt_secret)
            from sqlalchemy import select
            
            existing_key = await session.execute(
                select(ApiKey).where(ApiKey.key_hash == key_hash)
            )
            existing_key = existing_key.scalar_one_or_none()
            
            if existing_key:
                print(f"✅ API key already exists for JWT_SECRET_KEY!")
                print(f"📋 Name: {existing_key.name}")
                print(f"🏷️  Prefix: {existing_key.key_prefix}")
                print(f"📊 Active: {existing_key.is_active}")
                return jwt_secret, existing_key.key_prefix
            
            # Create API key with the JWT secret as the raw key
            key_prefix = ApiKey.get_key_prefix(jwt_secret)
            
            api_key = ApiKey(
                key_hash=key_hash,
                key_prefix=key_prefix,
                name="GitHub Actions (JWT)",
                description="API key created from JWT_SECRET_KEY for GitHub Actions workflows",
                rate_limit_per_minute=200,  # Higher limits for workflow usage
                rate_limit_per_hour=2000,
                rate_limit_per_day=20000,
                is_active=True
            )
            
            # Add to database
            session.add(api_key)
            await session.commit()
            
            return jwt_secret, api_key.key_prefix
            
    finally:
        await engine.dispose()


def main():
    try:
        raw_key, key_prefix = asyncio.run(create_jwt_api_key())
        
        print("")
        print("✅ GitHub Actions API authentication configured!")
        print(f"🔑 Using JWT_SECRET_KEY as API Key")
        print(f"🏷️  Prefix: {key_prefix}")
        print("")
        print("🎯 Both workflows will now use API mode successfully:")
        print("   - Stock Price Alert workflow")
        print("   - USD Rate Email workflow")
        print("")
        print("📝 No additional GitHub secrets needed - using existing JWT_SECRET_KEY")
        
    except Exception as e:
        print(f"❌ Error creating JWT API key: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Database connectivity checker script for deployment validation.
"""
import asyncio
import sys
import os

# Add the app directory to Python path for container execution
sys.path.insert(0, '/app')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine
from sqlalchemy import text

async def check_db():
    """Check database connectivity by executing a simple query."""
    try:
        async with engine.begin() as conn:
            await conn.execute(text('SELECT 1'))
        print('✅ Database connection successful')
        return True
    except Exception as e:
        print(f'❌ Database connection failed: {e}')
        return False

if __name__ == "__main__":
    result = asyncio.run(check_db())
    sys.exit(0 if result else 1)
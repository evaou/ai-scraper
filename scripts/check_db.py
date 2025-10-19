#!/usr/bin/env python3
"""
Database connectivity checker script for deployment validation.
"""
import asyncio
import sys
from app.core.database import get_engine

async def check_db():
    """Check database connectivity by executing a simple query."""
    try:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.execute('SELECT 1')
        print('✅ Database connection successful')
        return True
    except Exception as e:
        print(f'❌ Database connection failed: {e}')
        return False

if __name__ == "__main__":
    result = asyncio.run(check_db())
    sys.exit(0 if result else 1)
#!/usr/bin/env python3
"""
Test script to verify database schema initialization works correctly.
"""
import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import engine


async def test_schema():
    """Test that the schema is working correctly."""
    print("🧪 Testing database schema...")
    
    try:
        async with engine.begin() as conn:
            # Test basic connectivity
            await conn.execute(text("SELECT 1"))
            print("✅ Database connection works")
            
            # Test ENUM type works
            await conn.execute(text("""
                SELECT 'pending'::jobstatus
            """))
            print("✅ jobstatus ENUM type works")
            
            # Test table structure (insert/select test)
            from uuid import uuid4
            test_id = uuid4()
            
            await conn.execute(text("""
                INSERT INTO jobs (id, url, status, retry_count, max_retries, priority)
                VALUES (:id, 'https://test.com', 'pending', 0, 3, 0)
            """), {"id": test_id})
            
            result = await conn.execute(text("""
                SELECT status FROM jobs WHERE id = :id
            """), {"id": test_id})
            
            status = result.scalar()
            if status == 'pending':
                print("✅ Jobs table insert/select works")
            else:
                print(f"❌ Unexpected status: {status}")
                return False
            
            # Clean up test data
            await conn.execute(text("DELETE FROM jobs WHERE id = :id"), {"id": test_id})
            print("✅ Test data cleaned up")
            
            return True
            
    except Exception as e:
        print(f"❌ Schema test failed: {e}")
        return False


async def main():
    """Main test function."""
    print("🔬 Database Schema Test")
    print("=" * 30)
    
    success = await test_schema()
    
    if success:
        print("\n🎉 All schema tests passed!")
        return 0
    else:
        print("\n❌ Schema tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
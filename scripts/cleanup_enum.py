#!/usr/bin/env python3
"""
Database cleanup script to handle ENUM type conflicts.

This script can be used to clean up conflicting ENUM types
when migrations fail due to "type already exists" errors.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import engine


async def cleanup_enum_types():
    """Clean up conflicting ENUM types."""
    try:
        async with engine.begin() as conn:
            print("🔍 Checking for existing jobstatus enum type...")
            
            # Check if the enum type exists
            result = await conn.execute(text(
                "SELECT typname FROM pg_type WHERE typname = 'jobstatus'"
            ))
            existing_types = result.fetchall()
            
            if existing_types:
                print("⚠️  Found existing jobstatus enum type")
                
                # Check if any tables are using this type
                usage_check = await conn.execute(text("""
                    SELECT table_name, column_name 
                    FROM information_schema.columns 
                    WHERE udt_name = 'jobstatus'
                """))
                usages = usage_check.fetchall()
                
                if usages:
                    print("❌ Cannot drop enum type - it's being used by:")
                    for table, column in usages:
                        print(f"   - {table}.{column}")
                    print("📝 You may need to drop and recreate the jobs table")
                    return False
                else:
                    print("🗑️  Dropping unused jobstatus enum type...")
                    await conn.execute(text("DROP TYPE jobstatus"))
                    print("✅ Successfully dropped jobstatus enum type")
            else:
                print("✅ No conflicting jobstatus enum type found")
            
            return True
            
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return False


async def main():
    """Main cleanup function."""
    print("🧹 Database ENUM Type Cleanup")
    print("=" * 40)
    
    success = await cleanup_enum_types()
    
    if success:
        print("\n🎉 Cleanup completed successfully")
        print("📝 You can now run: alembic upgrade head")
    else:
        print("\n❌ Cleanup failed")
        print("📝 Manual intervention may be required")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
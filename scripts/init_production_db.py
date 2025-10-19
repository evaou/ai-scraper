#!/usr/bin/env python3
"""
Production Schema Initialization Script

This script initializes the database schema for production deployment,
handling conflicts and ensuring a clean state.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, '/app')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import engine, Base
from app.models import api_key, job, result  # Import all models


async def check_and_handle_schema():
    """Check schema state and handle conflicts intelligently."""
    print("🔍 Checking database schema state...")
    
    try:
        async with engine.begin() as conn:
            # Check if tables exist
            tables_result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('jobs', 'api_keys', 'results')
            """))
            existing_tables = [row[0] for row in tables_result.fetchall()]
            
            # Check if ENUM types exist
            enum_result = await conn.execute(text("""
                SELECT typname 
                FROM pg_type 
                WHERE typname = 'jobstatus'
            """))
            existing_enums = [row[0] for row in enum_result.fetchall()]
            
            # Determine action based on current state
            if len(existing_tables) == 3 and 'jobstatus' in existing_enums:
                print("✅ Schema already exists and appears complete")
                return 'complete'
            elif len(existing_tables) > 0 or existing_enums:
                print("⚠️  Partial schema detected - needs cleanup")
                return 'cleanup_needed'
            else:
                print("📝 Fresh database - ready for initialization")
                return 'initialize'
                
    except Exception as e:
        print(f"❌ Error checking schema: {e}")
        return 'error'


async def cleanup_partial_schema():
    """Clean up partial or conflicting schema elements."""
    print("🧹 Cleaning up partial schema...")
    
    try:
        async with engine.begin() as conn:
            # Drop tables if they exist
            await conn.execute(text("DROP TABLE IF EXISTS results CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS api_keys CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS jobs CASCADE"))
            
            # Drop ENUM types if they exist
            await conn.execute(text("DROP TYPE IF EXISTS jobstatus CASCADE"))
            
            # Drop alembic version table
            await conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))
            
            print("✅ Cleanup completed")
            return True
            
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return False


async def initialize_schema():
    """Initialize fresh schema from models."""
    print("🏗️  Initializing database schema...")
    
    try:
        async with engine.begin() as conn:
            # Create all tables from models
            await conn.run_sync(Base.metadata.create_all)
            
            # Set up Alembic version tracking
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS alembic_version (
                    version_num VARCHAR(32) NOT NULL,
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                )
            """))
            
            # Mark as migrated to avoid future conflicts
            await conn.execute(text("""
                INSERT INTO alembic_version (version_num) VALUES ('001')
                ON CONFLICT (version_num) DO NOTHING
            """))
            
            print("✅ Schema initialized successfully")
            return True
            
    except Exception as e:
        print(f"❌ Error initializing schema: {e}")
        return False


async def verify_deployment_ready():
    """Verify the database is ready for the application."""
    print("✅ Verifying deployment readiness...")
    
    try:
        async with engine.begin() as conn:
            # Test basic connectivity
            await conn.execute(text("SELECT 1"))
            
            # Verify tables exist
            tables_result = await conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('jobs', 'api_keys', 'results')
            """))
            table_count = tables_result.scalar()
            
            if table_count != 3:
                print(f"❌ Expected 3 tables, found {table_count}")
                return False
            
            # Verify ENUM exists
            enum_result = await conn.execute(text("""
                SELECT COUNT(*) 
                FROM pg_type 
                WHERE typname = 'jobstatus'
            """))
            enum_count = enum_result.scalar()
            
            if enum_count != 1:
                print(f"❌ Expected 1 jobstatus enum, found {enum_count}")
                return False
            
            print("✅ Database is deployment ready")
            return True
            
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


async def main():
    """Main deployment schema initialization."""
    print("🚀 Production Database Schema Initialization")
    print("=" * 50)
    
    # Check current schema state
    state = await check_and_handle_schema()
    
    if state == 'complete':
        print("✅ Schema is already complete")
        
    elif state == 'cleanup_needed':
        print("🧹 Cleaning up conflicting schema...")
        if not await cleanup_partial_schema():
            return 1
        
        print("🏗️  Initializing fresh schema...")
        if not await initialize_schema():
            return 1
            
    elif state == 'initialize':
        print("🏗️  Initializing fresh schema...")
        if not await initialize_schema():
            return 1
            
    else:  # error state
        print("❌ Unable to determine schema state")
        return 1
    
    # Final verification
    if not await verify_deployment_ready():
        return 1
    
    print("\n🎉 Database schema initialization completed!")
    print("📝 Application is ready to start")
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
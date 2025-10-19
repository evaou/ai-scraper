#!/usr/bin/env python3
"""
PostgreSQL Schema Reset Script

This script completely drops and recreates the database schema,
bypassing all migration conflicts. Use this for deployment when
migrations are causing issues.

WARNING: This will destroy all existing data!
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import engine, Base
from app.models import api_key, job, result  # Import all models


async def drop_all_schema():
    """Drop all database objects to start fresh."""
    print("🗑️  Dropping all database objects...")
    
    try:
        async with engine.begin() as conn:
            # Drop all tables first (this also drops dependent objects)
            print("  - Dropping all tables...")
            await conn.run_sync(Base.metadata.drop_all)
            
            # Drop any remaining enum types
            print("  - Cleaning up ENUM types...")
            await conn.execute(text("""
                DO $$ DECLARE
                    r RECORD;
                BEGIN
                    FOR r IN (SELECT typname FROM pg_type WHERE typname IN ('jobstatus')) LOOP
                        EXECUTE 'DROP TYPE IF EXISTS ' || quote_ident(r.typname) || ' CASCADE';
                    END LOOP;
                END $$;
            """))
            
            # Drop any remaining sequences
            print("  - Cleaning up sequences...")
            await conn.execute(text("""
                DO $$ DECLARE
                    r RECORD;
                BEGIN
                    FOR r IN (SELECT schemaname, sequencename FROM pg_sequences WHERE schemaname = 'public') LOOP
                        EXECUTE 'DROP SEQUENCE IF EXISTS ' || quote_ident(r.schemaname) || '.' || quote_ident(r.sequencename) || ' CASCADE';
                    END LOOP;
                END $$;
            """))
            
            print("✅ All database objects dropped successfully")
            return True
            
    except Exception as e:
        print(f"❌ Error dropping schema: {e}")
        return False


async def create_fresh_schema():
    """Create a fresh schema from SQLAlchemy models."""
    print("🏗️  Creating fresh database schema...")
    
    try:
        async with engine.begin() as conn:
            # Create all tables from models
            print("  - Creating tables from models...")
            await conn.run_sync(Base.metadata.create_all)
            
            print("✅ Fresh schema created successfully")
            return True
            
    except Exception as e:
        print(f"❌ Error creating schema: {e}")
        return False


async def verify_schema():
    """Verify the schema was created correctly."""
    print("🔍 Verifying database schema...")
    
    try:
        async with engine.begin() as conn:
            # Check tables exist
            tables_result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            tables = [row[0] for row in tables_result.fetchall()]
            
            expected_tables = ['api_keys', 'jobs', 'results']
            missing_tables = set(expected_tables) - set(tables)
            
            if missing_tables:
                print(f"❌ Missing tables: {missing_tables}")
                return False
            
            print(f"✅ Found expected tables: {tables}")
            
            # Check ENUM types
            enum_result = await conn.execute(text("""
                SELECT typname 
                FROM pg_type 
                WHERE typname = 'jobstatus'
            """))
            enums = [row[0] for row in enum_result.fetchall()]
            
            if 'jobstatus' not in enums:
                print("❌ Missing jobstatus ENUM type")
                return False
            
            print("✅ ENUM types created correctly")
            
            # Test basic operations
            await conn.execute(text("SELECT 1"))
            print("✅ Database connectivity verified")
            
            return True
            
    except Exception as e:
        print(f"❌ Error verifying schema: {e}")
        return False


async def reset_alembic_version():
    """Reset Alembic version table to mark as migrated."""
    print("🔄 Resetting Alembic version tracking...")
    
    try:
        async with engine.begin() as conn:
            # Drop existing alembic_version table if it exists
            await conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
            
            # Create fresh alembic_version table
            await conn.execute(text("""
                CREATE TABLE alembic_version (
                    version_num VARCHAR(32) NOT NULL,
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                )
            """))
            
            # Mark as migrated to latest version
            await conn.execute(text("""
                INSERT INTO alembic_version (version_num) VALUES ('001')
            """))
            
            print("✅ Alembic version reset successfully")
            return True
            
    except Exception as e:
        print(f"❌ Error resetting Alembic version: {e}")
        return False


async def main():
    """Main schema reset function."""
    print("🔄 PostgreSQL Schema Reset")
    print("=" * 50)
    print("⚠️  WARNING: This will destroy all existing data!")
    print("=" * 50)
    
    # Step 1: Drop all existing schema
    if not await drop_all_schema():
        print("\n❌ Schema cleanup failed")
        return 1
    
    print()
    
    # Step 2: Create fresh schema
    if not await create_fresh_schema():
        print("\n❌ Schema creation failed")
        return 1
    
    print()
    
    # Step 3: Verify schema
    if not await verify_schema():
        print("\n❌ Schema verification failed")
        return 1
    
    print()
    
    # Step 4: Reset Alembic tracking
    if not await reset_alembic_version():
        print("\n❌ Alembic reset failed")
        return 1
    
    print()
    print("🎉 Database schema reset completed successfully!")
    print("📝 The database is now ready for use without migration conflicts")
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
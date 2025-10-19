#!/usr/bin/env python3
"""
Database Health Check Script

Quick health check to verify database schema and connectivity.
"""
import asyncio
import os
import sys

# Add the app directory to Python path
sys.path.insert(0, '/app')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import engine


async def health_check():
    """Perform a comprehensive database health check."""
    print("🏥 Database Health Check")
    print("=" * 30)
    
    try:
        async with engine.begin() as conn:
            # Test basic connectivity
            print("🔍 Testing database connectivity...")
            await conn.execute(text("SELECT 1"))
            print("✅ Database connection: OK")
            
            # Check tables
            print("🔍 Checking required tables...")
            tables_result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('jobs', 'api_keys', 'results')
                ORDER BY table_name
            """))
            tables = [row[0] for row in tables_result.fetchall()]
            
            if len(tables) == 3:
                print(f"✅ All required tables present: {tables}")
            else:
                print(f"❌ Missing tables. Found: {tables}")
                return False
            
            # Check ENUM type
            print("🔍 Checking ENUM types...")
            enum_result = await conn.execute(text("""
                SELECT typname FROM pg_type WHERE typname = 'jobstatus'
            """))
            enums = [row[0] for row in enum_result.fetchall()]
            
            if 'jobstatus' in enums:
                print("✅ JobStatus ENUM type: OK")
            else:
                print("❌ JobStatus ENUM type: MISSING")
                return False
            
            # Check Alembic version
            print("🔍 Checking migration status...")
            try:
                version_result = await conn.execute(text("""
                    SELECT version_num FROM alembic_version LIMIT 1
                """))
                version = version_result.scalar()
                print(f"✅ Alembic version: {version}")
            except Exception:
                print("⚠️  Alembic version table not found (may be OK)")
            
            # Test table constraints
            print("🔍 Testing table integrity...")
            
            # Test jobs table structure
            jobs_cols = await conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'jobs' 
                ORDER BY ordinal_position
            """))
            jobs_columns = [(row[0], row[1]) for row in jobs_cols.fetchall()]
            
            required_job_columns = ['id', 'url', 'status', 'created_at']
            job_column_names = [col[0] for col in jobs_columns]
            
            missing_job_cols = [col for col in required_job_columns if col not in job_column_names]
            if missing_job_cols:
                print(f"❌ Missing columns in jobs table: {missing_job_cols}")
                return False
            else:
                print("✅ Jobs table structure: OK")
            
            print("\n🎉 Database health check passed!")
            print("📝 All systems operational")
            return True
            
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(health_check())
    sys.exit(0 if success else 1)
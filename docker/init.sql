-- PostgreSQL initialization script for development environment
-- This script runs when the container starts for the first time

-- Create development database if not exists
SELECT 'CREATE DATABASE scraper'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'scraper')\gexec

-- Connect to the scraper database
\c scraper;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search and similarity
CREATE EXTENSION IF NOT EXISTS "btree_gin";  -- For GIN indexes on multiple column types

-- Create custom functions for application use
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create a function to generate URL hash for cache keys
CREATE OR REPLACE FUNCTION url_cache_hash(url TEXT, selector TEXT DEFAULT '', options JSONB DEFAULT '{}')
RETURNS TEXT AS $$
BEGIN
    RETURN encode(digest(url || COALESCE(selector, '') || COALESCE(options::text, '{}'), 'sha256'), 'hex');
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Set default configuration for better performance
ALTER DATABASE scraper SET log_statement = 'none';
ALTER DATABASE scraper SET log_min_duration_statement = 1000;  -- Log slow queries only
ALTER DATABASE scraper SET shared_preload_libraries = 'pg_stat_statements';

-- Create user for API access (if not using default postgres user)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'scraper_api') THEN
        CREATE USER scraper_api WITH PASSWORD 'api_password';
        GRANT CONNECT ON DATABASE scraper TO scraper_api;
        GRANT CREATE ON DATABASE scraper TO scraper_api;
        ALTER USER scraper_api SET search_path = public;
    END IF;
END $$;
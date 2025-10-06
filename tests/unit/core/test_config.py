"""Unit tests for configuration module."""

import os
import pytest
from unittest.mock import patch

from app.core.config import Settings, get_settings


class TestSettings:
    """Test cases for Settings class."""
    
    def test_default_settings(self):
        """Test default configuration values."""
        settings = Settings()
        
        # Project information
        assert settings.PROJECT_NAME == "Web Scraping API"
        assert settings.PROJECT_VERSION == "1.0.0"
        assert settings.API_V1_STR == "/api/v1"
        
        # Database defaults
        assert settings.DATABASE_URL == "postgresql+asyncpg://postgres:password@db:5432/scraper"
        assert settings.POSTGRES_DB == "scraper"
        assert settings.POSTGRES_USER == "postgres"
        assert settings.POSTGRES_PASSWORD == "password"
        
        # API defaults
        assert settings.API_HOST == "0.0.0.0"
        assert settings.API_PORT == 8000
        assert settings.API_WORKERS == 1
        assert settings.API_KEY_REQUIRED is False
        assert settings.CORS_ORIGINS == ["*"]
        
        # Redis defaults
        assert settings.REDIS_URL == "redis://redis:6379/0"
        assert settings.REDIS_POOL_SIZE == 10
        assert settings.REDIS_POOL_MAX_CONNECTIONS == 20
        
        # Scraping defaults
        assert settings.SCRAPE_TIMEOUT == 30
        assert settings.WORKER_CONCURRENCY == 3
        assert settings.PLAYWRIGHT_BROWSER == "chromium"
        assert settings.headless is True
        assert settings.max_concurrency == 3
        assert settings.max_retries == 3
        
        # Cache defaults
        assert settings.CACHE_TTL == 3600
        assert settings.JOB_STATUS_TTL == 86400
        assert settings.RESULT_CACHE_TTL == 86400
        
        # Logging defaults
        assert settings.LOG_LEVEL == "INFO"
        assert settings.LOG_FORMAT == "json"
        assert settings.DEBUG is True
        assert settings.RELOAD is False
    
    def test_custom_settings_values(self):
        """Test creating settings with custom values."""
        settings = Settings(
            PROJECT_NAME="Custom Scraper",
            API_PORT=9000,
            DEBUG=False,
            PLAYWRIGHT_BROWSER="firefox",
            LOG_LEVEL="ERROR",
            WORKER_CONCURRENCY=5
        )
        
        assert settings.PROJECT_NAME == "Custom Scraper"
        assert settings.API_PORT == 9000
        assert settings.DEBUG is False
        assert settings.PLAYWRIGHT_BROWSER == "firefox"
        assert settings.LOG_LEVEL == "ERROR"
        assert settings.WORKER_CONCURRENCY == 5
    
    @patch.dict(os.environ, {
        "PROJECT_NAME": "Env Scraper",
        "API_PORT": "8080",
        "DEBUG": "false",
        "LOG_LEVEL": "WARNING",
        "REDIS_URL": "redis://localhost:6380/1",
        "DATABASE_URL": "postgresql://user:pass@localhost/testdb"
    })
    def test_environment_variable_override(self):
        """Test that environment variables override defaults."""
        settings = Settings()
        
        assert settings.PROJECT_NAME == "Env Scraper"
        assert settings.API_PORT == 8080
        assert settings.DEBUG is False
        assert settings.LOG_LEVEL == "WARNING"
        assert settings.REDIS_URL == "redis://localhost:6380/1"
        assert settings.DATABASE_URL == "postgresql://user:pass@localhost/testdb"
    
    def test_browser_enum_validation(self):
        """Test browser enum validation."""
        # Valid browsers
        for browser in ["chromium", "firefox", "webkit"]:
            settings = Settings(PLAYWRIGHT_BROWSER=browser)
            assert settings.PLAYWRIGHT_BROWSER == browser
        
        # Invalid browser should raise validation error
        with pytest.raises(ValueError):
            Settings(PLAYWRIGHT_BROWSER="invalid_browser")
    
    def test_log_level_validation(self):
        """Test log level validation."""
        # Valid log levels
        for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            settings = Settings(LOG_LEVEL=level)
            assert settings.LOG_LEVEL == level
        
        # Invalid log level should raise validation error
        with pytest.raises(ValueError):
            Settings(LOG_LEVEL="INVALID")
    
    def test_user_agents_list(self):
        """Test that user agents list is properly configured."""
        settings = Settings()
        
        assert isinstance(settings.USER_AGENTS, list)
        assert len(settings.USER_AGENTS) > 0
        
        # All user agents should be strings
        for ua in settings.USER_AGENTS:
            assert isinstance(ua, str)
            assert len(ua) > 0
            assert "Mozilla" in ua  # Basic check for valid user agent format
    
    def test_numeric_field_validation(self):
        """Test validation of numeric fields."""
        settings = Settings()
        
        # Check that numeric fields have proper types and reasonable values
        assert isinstance(settings.API_PORT, int)
        assert 1 <= settings.API_PORT <= 65535
        
        assert isinstance(settings.SCRAPE_TIMEOUT, int)
        assert settings.SCRAPE_TIMEOUT > 0
        
        assert isinstance(settings.WORKER_CONCURRENCY, int)
        assert settings.WORKER_CONCURRENCY > 0
        
        assert isinstance(settings.CACHE_TTL, int)
        assert settings.CACHE_TTL > 0
        
        assert isinstance(settings.max_retries, int)
        assert settings.max_retries >= 0
    
    def test_boolean_field_validation(self):
        """Test validation of boolean fields."""
        settings = Settings()
        
        assert isinstance(settings.DEBUG, bool)
        assert isinstance(settings.RELOAD, bool)
        assert isinstance(settings.headless, bool)
        assert isinstance(settings.API_KEY_REQUIRED, bool)
        assert isinstance(settings.SCREENSHOT_ENABLED, bool)
        assert isinstance(settings.EXTRACT_LINKS_ENABLED, bool)
    
    def test_timeout_configurations(self):
        """Test timeout-related configurations."""
        settings = Settings()
        
        assert settings.SCRAPE_TIMEOUT > 0
        assert settings.default_timeout > 0
        assert settings.navigation_timeout > 0
        assert settings.HEALTH_CHECK_TIMEOUT > 0
        
        # Timeouts should be reasonable (not too high or too low)
        assert 5 <= settings.SCRAPE_TIMEOUT <= 300
        assert 5 <= settings.default_timeout <= 300
        assert 5 <= settings.navigation_timeout <= 300
        assert 1 <= settings.HEALTH_CHECK_TIMEOUT <= 60
    
    def test_backoff_configuration(self):
        """Test exponential backoff configuration."""
        settings = Settings()
        
        assert settings.backoff_base > 0
        assert settings.backoff_max > 0
        assert settings.backoff_max > settings.backoff_base
        
        # Backoff values should be reasonable
        assert 0.1 <= settings.backoff_base <= 10.0
        assert 10.0 <= settings.backoff_max <= 300.0
    
    def test_pool_size_configurations(self):
        """Test connection pool configurations."""
        settings = Settings()
        
        # Database pool settings
        assert settings.DB_POOL_SIZE > 0
        assert settings.DB_MAX_OVERFLOW >= 0
        assert isinstance(settings.DB_POOL_PRE_PING, bool)
        assert isinstance(settings.DB_ECHO, bool)
        
        # Redis pool settings
        assert settings.REDIS_POOL_SIZE > 0
        assert settings.REDIS_POOL_MAX_CONNECTIONS > 0
        assert settings.REDIS_POOL_MAX_CONNECTIONS >= settings.REDIS_POOL_SIZE
    
    def test_rate_limiting_configuration(self):
        """Test rate limiting configurations."""
        settings = Settings()
        
        assert settings.RATE_LIMIT_PER_MINUTE > 0
        assert settings.RATE_LIMIT_PER_HOUR > 0
        
        # Per hour should be higher than per minute
        assert settings.RATE_LIMIT_PER_HOUR >= settings.RATE_LIMIT_PER_MINUTE
        
        # Values should be reasonable
        assert 1 <= settings.RATE_LIMIT_PER_MINUTE <= 10000
        assert 1 <= settings.RATE_LIMIT_PER_HOUR <= 100000
    
    def test_content_size_limits(self):
        """Test content size limit configurations."""
        settings = Settings()
        
        assert settings.MAX_CONTENT_SIZE > 0
        
        # Should be at least 1MB but not more than 1GB
        assert 1024 * 1024 <= settings.MAX_CONTENT_SIZE <= 1024 * 1024 * 1024


class TestGetSettings:
    """Test cases for get_settings function."""
    
    def test_get_settings_returns_singleton(self):
        """Test that get_settings returns the same instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        
        assert settings1 is settings2
        assert id(settings1) == id(settings2)
    
    def test_get_settings_returns_settings_instance(self):
        """Test that get_settings returns a Settings instance."""
        settings = get_settings()
        
        assert isinstance(settings, Settings)
        assert hasattr(settings, 'PROJECT_NAME')
        assert hasattr(settings, 'DATABASE_URL')
        assert hasattr(settings, 'REDIS_URL')
    
    @patch('app.core.config._settings', None)
    def test_get_settings_creates_new_instance_when_none(self):
        """Test that get_settings creates a new instance when global is None."""
        # Clear the global settings
        import app.core.config
        app.core.config._settings = None
        
        settings = get_settings()
        
        assert isinstance(settings, Settings)
        assert app.core.config._settings is not None
        assert app.core.config._settings is settings
    
    def test_settings_field_descriptions(self):
        """Test that settings fields have proper descriptions."""
        settings = Settings()
        
        # Check that Field descriptions are accessible through model fields
        fields = settings.__class__.model_fields
        
        # Some key fields should have descriptions
        assert 'description' in str(fields['PROJECT_NAME'])
        assert 'description' in str(fields['DATABASE_URL'])
        assert 'description' in str(fields['API_HOST'])
        assert 'description' in str(fields['LOG_LEVEL'])
    
    @pytest.mark.parametrize("env_var,expected_type", [
        ("API_PORT", int),
        ("DEBUG", bool),
        ("WORKER_CONCURRENCY", int),
        ("CACHE_TTL", int),
        ("API_KEY_REQUIRED", bool),
        ("CORS_ORIGINS", list),
    ])
    def test_environment_variable_type_conversion(self, env_var, expected_type):
        """Test that environment variables are properly converted to expected types."""
        test_values = {
            "API_PORT": "9000",
            "DEBUG": "true",
            "WORKER_CONCURRENCY": "5",
            "CACHE_TTL": "1800",
            "API_KEY_REQUIRED": "false",
            "CORS_ORIGINS": '["http://localhost:3000", "https://app.example.com"]'
        }
        
        if env_var in test_values:
            with patch.dict(os.environ, {env_var: test_values[env_var]}):
                settings = Settings()
                value = getattr(settings, env_var)
                assert isinstance(value, expected_type)
    
    def test_config_class_attributes(self):
        """Test Config class attributes."""
        config = Settings.Config
        
        assert config.env_file == ".env"
        assert config.env_file_encoding == "utf-8"
        assert config.case_sensitive is False
    
    def test_celery_configuration(self):
        """Test Celery-specific configuration."""
        settings = Settings()
        
        assert settings.CELERY_BROKER_URL.startswith("redis://")
        assert settings.CELERY_RESULT_BACKEND.startswith("redis://")
        assert settings.CELERY_WORKER_CONCURRENCY > 0
        
        # Celery URLs should be different databases
        assert "/1" in settings.CELERY_BROKER_URL
        assert "/2" in settings.CELERY_RESULT_BACKEND
    
    def test_security_related_settings(self):
        """Test security-related configuration."""
        settings = Settings()
        
        # JWT secret should exist and not be empty
        assert settings.JWT_SECRET_KEY
        assert len(settings.JWT_SECRET_KEY) > 10
        
        # API key header should be reasonable
        assert settings.API_KEY_HEADER
        assert len(settings.API_KEY_HEADER) > 3
        assert "X-" in settings.API_KEY_HEADER
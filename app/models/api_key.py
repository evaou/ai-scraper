"""API Key model for authentication."""
import hashlib
import secrets
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func

from app.core.database import Base


class ApiKey(Base):
    """Model for API keys."""

    __tablename__ = "api_keys"

    # Primary key
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)

    # API key details
    key_hash = Column(String(128), unique=True, nullable=False, index=True)
    key_prefix = Column(String(10), nullable=False, index=True)  # First 8 chars for identification
    name = Column(String(100), nullable=True)
    description = Column(String(500), nullable=True)

    # Rate limiting
    rate_limit_per_minute = Column(Integer, nullable=False, default=100)
    rate_limit_per_hour = Column(Integer, nullable=False, default=1000)
    rate_limit_per_day = Column(Integer, nullable=False, default=10000)

    # Status
    is_active = Column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Usage statistics
    total_requests = Column(Integer, nullable=False, default=0)

    # Additional indexes for performance
    __table_args__ = (
        Index("ix_api_keys_active_last_used", "is_active", "last_used_at"),
        Index("ix_api_keys_expires_active", "expires_at", "is_active"),
    )

    def __repr__(self) -> str:
        """String representation of the API key."""
        return f"<ApiKey(id={self.id}, prefix={self.key_prefix}, name={self.name})>"

    @classmethod
    def generate_key(cls) -> str:
        """Generate a new API key."""
        return f"sk-{secrets.token_urlsafe(32)}"

    @classmethod
    def hash_key(cls, key: str) -> str:
        """Hash an API key for storage."""
        return hashlib.sha256(key.encode()).hexdigest()

    @classmethod
    def get_key_prefix(cls, key: str) -> str:
        """Get the prefix of an API key."""
        return key[:8] if len(key) >= 8 else key

    @classmethod
    def create_api_key(
        cls,
        name: str | None = None,
        description: str | None = None,
        rate_limit_per_minute: int = 100,
        rate_limit_per_hour: int = 1000,
        rate_limit_per_day: int = 10000,
        expires_at: datetime | None = None,
    ) -> tuple["ApiKey", str]:
        """
        Create a new API key.

        Returns:
            tuple: (ApiKey instance, raw key string)
        """
        raw_key = cls.generate_key()
        key_hash = cls.hash_key(raw_key)
        key_prefix = cls.get_key_prefix(raw_key)

        api_key = cls(
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=name,
            description=description,
            rate_limit_per_minute=rate_limit_per_minute,
            rate_limit_per_hour=rate_limit_per_hour,
            rate_limit_per_day=rate_limit_per_day,
            expires_at=expires_at,
        )

        return api_key, raw_key

    def verify_key(self, raw_key: str) -> bool:
        """Verify a raw key against this API key."""
        return self.key_hash == self.hash_key(raw_key)

    @property
    def is_expired(self) -> bool:
        """Check if the API key is expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if the API key is valid (active and not expired)."""
        return self.is_active and not self.is_expired

    def update_last_used(self) -> None:
        """Update the last used timestamp."""
        self.last_used_at = datetime.utcnow()
        self.total_requests += 1

    def to_dict(self) -> dict[str, Any]:
        """Convert API key to dictionary (excluding sensitive data)."""
        return {
            "id": str(self.id),
            "key_prefix": self.key_prefix,
            "name": self.name,
            "description": self.description,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "rate_limit_per_hour": self.rate_limit_per_hour,
            "rate_limit_per_day": self.rate_limit_per_day,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "total_requests": self.total_requests,
            "is_expired": self.is_expired,
            "is_valid": self.is_valid,
        }

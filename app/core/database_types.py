"""Database type compatibility utilities for cross-database support."""

from sqlalchemy import JSON, Text
from sqlalchemy.dialects.postgresql import JSONB as PostgresJSONB, UUID as PostgresUUID
from sqlalchemy.sql import type_api
from sqlalchemy.types import TypeDecorator
import uuid as uuid_lib


class JSONType(TypeDecorator):
    """Cross-database JSON type that uses JSONB for PostgreSQL and JSON for others."""
    
    impl = JSON
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        """Load the appropriate dialect-specific implementation."""
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgresJSONB())
        else:
            return dialect.type_descriptor(JSON())


class UUIDType(TypeDecorator):
    """Cross-database UUID type that uses PostgreSQL UUID for PostgreSQL and Text for others."""
    
    impl = Text
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        """Load the appropriate dialect-specific implementation."""
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgresUUID(as_uuid=True))
        else:
            return dialect.type_descriptor(Text())
    
    def process_bind_param(self, value, dialect):
        """Process values being sent to the database."""
        if value is None:
            return value
        if dialect.name == 'postgresql':
            return value
        else:
            # For non-PostgreSQL, convert UUID to string
            if isinstance(value, uuid_lib.UUID):
                return str(value)
            return value
    
    def process_result_value(self, value, dialect):
        """Process values being returned from the database."""
        if value is None:
            return value
        if dialect.name == 'postgresql':
            return value
        else:
            # For non-PostgreSQL, convert string back to UUID
            if isinstance(value, str):
                return uuid_lib.UUID(value)
            return value
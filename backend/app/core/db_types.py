"""Cross-database type compatibility — works on PostgreSQL and SQLite."""

import uuid
from sqlalchemy.types import TypeDecorator, CHAR, String, JSON

# Detect backend
from app.config import settings
IS_SQLITE = settings.DATABASE_URL.startswith("sqlite")


class UniversalUUID(TypeDecorator):
    """UUID type that works on PostgreSQL (native UUID) and SQLite (CHAR(36))."""
    impl = CHAR(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import UUID as PGUUID
            return dialect.type_descriptor(PGUUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return str(value) if dialect.name == "sqlite" else value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)


class UniversalJSON(TypeDecorator):
    """JSON type that works on PostgreSQL (JSONB) and SQLite (JSON)."""
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import JSONB
            return dialect.type_descriptor(JSONB)
        return dialect.type_descriptor(JSON)


class UniversalINET(TypeDecorator):
    """INET type — uses native INET on PostgreSQL, String on SQLite."""
    impl = String(50)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import INET
            return dialect.type_descriptor(INET)
        return dialect.type_descriptor(String(50))

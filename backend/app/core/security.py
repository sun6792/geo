"""JWT token management, password hashing, and authentication utilities."""

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import settings

# ── Password hashing ──────────────────────────────────────────────


def hash_password(password: str) -> str:
    """Hash a plain-text password with bcrypt."""
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against its bcrypt hash."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


# ── JWT Token management ──────────────────────────────────────────


def create_access_token(user_id: uuid.UUID, customer_id: uuid.UUID, is_super_admin: bool = False) -> str:
    """Create a short-lived JWT access token."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "cid": str(customer_id),
        "isa": is_super_admin,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: uuid.UUID, customer_id: uuid.UUID) -> str:
    """Create a long-lived JWT refresh token."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "cid": str(customer_id),
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token. Raises JWTError on failure."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


# ── Client review token ───────────────────────────────────────────


def create_client_review_token(review_id: uuid.UUID, customer_id: uuid.UUID, expires_hours: int = 72) -> str:
    """Create a one-time access token for external client reviewers."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(review_id),
        "cid": str(customer_id),
        "type": "client_review",
        "iat": now,
        "exp": now + timedelta(hours=expires_hours),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def generate_client_access_token() -> str:
    """Generate a random URL-safe token for client review access (stored in DB, not JWT)."""
    import secrets
    return secrets.token_urlsafe(32)

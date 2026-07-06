"""Authentication service: login, token management, session handling."""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.models.account import LoginAudit, User, UserSession


class AuthService:
    """Handles authentication workflows."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def login(self, email: str, password: str, request: Request) -> dict:
        """Authenticate user by email + password. Returns token pair on success."""
        # Find user
        result = await self.db.execute(select(User).where(User.email == email, User.is_active == True))
        user = result.scalar_one_or_none()

        ip = request.client.host if request.client else "unknown"
        ua = request.headers.get("User-Agent", "unknown")

        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

        # Create tokens
        access_token = create_access_token(user.id, user.customer_id, user.is_super_admin)
        refresh_token = create_refresh_token(user.id, user.customer_id)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user_id": str(user.id),
            "customer_id": str(user.customer_id),
            "display_name": user.display_name,
            "is_super_admin": user.is_super_admin,
        }

    async def refresh(self, refresh_token: str) -> dict:
        """Issue a new access token using a valid refresh token."""
        from app.core.security import decode_token

        try:
            payload = decode_token(refresh_token)
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

        user_id = uuid.UUID(payload["sub"])
        customer_id = uuid.UUID(payload["cid"])

        # Verify token hash exists and is not revoked
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        result = await self.db.execute(
            select(UserSession).where(
                UserSession.user_id == user_id,
                UserSession.refresh_token_hash == token_hash,
                UserSession.revoked_at.is_(None),
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked or expired")

        # Verify user still active
        result = await self.db.execute(select(User).where(User.id == user_id, User.is_active == True))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive")

        # Revoke old refresh token
        session.revoked_at = datetime.now(timezone.utc)

        # Issue new tokens
        new_access = create_access_token(user.id, customer_id, user.is_super_admin)
        new_refresh = create_refresh_token(user.id, customer_id)

        # Store new refresh session
        new_hash = hashlib.sha256(new_refresh.encode()).hexdigest()
        self.db.add(UserSession(
            user_id=user.id,
            refresh_token_hash=new_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        ))

        return {
            "access_token": new_access,
            "refresh_token": new_refresh,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    async def logout(self, refresh_token: str, user_id: uuid.UUID) -> None:
        """Revoke a refresh token session."""
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        result = await self.db.execute(
            select(UserSession).where(
                UserSession.user_id == user_id,
                UserSession.refresh_token_hash == token_hash,
                UserSession.revoked_at.is_(None),
            )
        )
        session = result.scalar_one_or_none()
        if session:
            session.revoked_at = datetime.now(timezone.utc)

    async def change_password(self, user_id: uuid.UUID, old_password: str, new_password: str) -> None:
        """Change a user's password after verifying the old one."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if not verify_password(old_password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Old password is incorrect")
        user.password_hash = hash_password(new_password)
        # Revoke all sessions for security
        result = await self.db.execute(
            select(UserSession).where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
        )
        for s in result.scalars().all():
            s.revoked_at = datetime.now(timezone.utc)

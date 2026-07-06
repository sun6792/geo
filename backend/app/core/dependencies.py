"""Shared FastAPI dependencies for authentication and authorization."""

import uuid
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token


# ── Token extraction ──────────────────────────────────────────────


async def get_token_from_header(authorization: Optional[str] = Header(None)) -> str:
    """Extract Bearer token from the Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Authorization header")
    return authorization.removeprefix("Bearer ").strip()


# ── Current user ──────────────────────────────────────────────────


async def get_current_user(
    token: str = Depends(get_token_from_header),
    db: AsyncSession = Depends(get_db),
):
    """Validate access token and return the current user's identity + roles."""
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token type must be 'access'")

    user_id = uuid.UUID(payload["sub"])
    customer_id = uuid.UUID(payload["cid"])
    is_super_admin = payload.get("isa", False)

    # Deferred import to avoid circular dependency
    from app.models.account import User

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return {
        "user_id": user_id,
        "customer_id": customer_id,
        "is_super_admin": is_super_admin,
        "user": user,
    }


async def get_current_customer_id(request: Request) -> uuid.UUID:
    """Extract current customer ID from the request state (set by TenantMiddleware)."""
    cid = getattr(request.state, "customer_id", None)
    if cid is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing customer context")
    return uuid.UUID(cid) if isinstance(cid, str) else cid


# ── Permission checker ────────────────────────────────────────────


def require_permission(resource: str, action: str):
    """Factory: returns a FastAPI dependency that checks a specific permission."""

    async def _check(
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> dict:
        from app.models.account import UserRole, RolePermission, Permission

        user_id = current_user["user_id"]
        customer_id = current_user["customer_id"]

        # Super admin bypasses all permission checks
        if current_user["is_super_admin"]:
            return current_user

        # Check permission via user -> roles -> permissions
        perm_code = f"{resource}:{action}"
        result = await db.execute(
            select(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(UserRole, UserRole.role_id == RolePermission.role_id)
            .where(
                UserRole.user_id == user_id,
                Permission.code == perm_code,
            )
            .limit(1)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing permission: {perm_code}")

        return current_user

    return _check

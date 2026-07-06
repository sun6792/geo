"""Authentication endpoints: login, refresh, logout, profile."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_token_from_header
from app.schemas.account import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Authenticate with email + password. Returns JWT token pair."""
    svc = AuthService(db)
    result = await svc.login(body.email, body.password, request)
    return result


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Exchange a refresh token for a new access token pair."""
    svc = AuthService(db)
    return await svc.refresh(body.refresh_token)


@router.post("/logout")
async def logout(
    body: RefreshRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a refresh token (logout)."""
    svc = AuthService(db)
    await svc.logout(body.refresh_token, current_user["user_id"])
    return {"message": "Logged out successfully"}


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Return the current authenticated user's profile."""
    user = current_user["user"]
    # Manual serialization to avoid Pydantic nested relationship issues
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "phone": user.phone,
        "avatar_url": user.avatar_url,
        "is_super_admin": user.is_super_admin,
        "is_active": user.is_active,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "customer_id": str(user.customer_id),
        "roles": [],
    }


@router.patch("/password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change the current user's password."""
    svc = AuthService(db)
    await svc.change_password(current_user["user_id"], body.old_password, body.new_password)
    return {"message": "Password changed successfully"}

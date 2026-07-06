"""User management endpoints within a customer tenant."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.core.pagination import PaginationParams, PaginatedResponse
from app.schemas.account import AssignRolesRequest, UserCreate, UserResponse, UserUpdate
from app.services.account_service import AccountService

router = APIRouter(tags=["Users"])


@router.get("/", response_model=PaginatedResponse[UserResponse])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List users in the current customer tenant."""
    svc = AccountService(db, current_user["customer_id"])
    pagination = PaginationParams(page=page, page_size=page_size)
    items, total = await svc.list_users(pagination, search)
    return PaginatedResponse.create(items, total, pagination)


@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(
    body: UserCreate,
    current_user: dict = Depends(require_permission("account", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new user in the current tenant."""
    svc = AccountService(db, current_user["customer_id"])
    return await svc.create_user(
        email=body.email,
        password=body.password,
        display_name=body.display_name,
        phone=body.phone,
        role_ids=body.role_ids,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific user's details."""
    svc = AccountService(db, current_user["customer_id"])
    return await svc.get_user(user_id)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    current_user: dict = Depends(require_permission("account", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a user's profile."""
    svc = AccountService(db, current_user["customer_id"])
    return await svc.update_user(user_id, **body.model_dump(exclude_unset=True))


@router.delete("/{user_id}")
async def deactivate_user(
    user_id: uuid.UUID,
    current_user: dict = Depends(require_permission("account", "delete")),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a user (soft delete)."""
    svc = AccountService(db, current_user["customer_id"])
    await svc.deactivate_user(user_id)
    return {"message": "User deactivated"}


@router.post("/{user_id}/roles", response_model=UserResponse)
async def assign_roles(
    user_id: uuid.UUID,
    body: AssignRolesRequest,
    current_user: dict = Depends(require_permission("account", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Assign roles to a user (replaces existing roles)."""
    svc = AccountService(db, current_user["customer_id"])
    return await svc.assign_roles(user_id, body.role_ids)

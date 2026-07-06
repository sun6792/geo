"""Role management endpoints."""

import uuid

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.schemas.account import RoleCreate, RoleResponse, RoleUpdate
from app.services.account_service import AccountService

router = APIRouter(tags=["Roles"])


@router.get("/", response_model=list[RoleResponse])
async def list_roles(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all roles available to this tenant (system + custom)."""
    svc = AccountService(db, current_user["customer_id"])
    return await svc.list_roles()


@router.post("/", response_model=RoleResponse, status_code=201)
async def create_role(
    body: RoleCreate,
    current_user: dict = Depends(require_permission("account", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a custom role for this tenant."""
    svc = AccountService(db, current_user["customer_id"])
    return await svc.create_role(
        name=body.name,
        code=body.code,
        description=body.description,
        permission_ids=body.permission_ids,
    )


@router.patch("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: uuid.UUID,
    body: RoleUpdate,
    current_user: dict = Depends(require_permission("account", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a custom role."""
    svc = AccountService(db, current_user["customer_id"])
    return await svc.update_role(role_id, **body.model_dump(exclude_unset=True))


@router.delete("/{role_id}")
async def delete_role(
    role_id: uuid.UUID,
    current_user: dict = Depends(require_permission("account", "delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a custom role."""
    svc = AccountService(db, current_user["customer_id"])
    await svc.delete_role(role_id)
    return {"message": "Role deleted"}


@router.post("/{role_id}/permissions", response_model=RoleResponse)
async def set_role_permissions(
    role_id: uuid.UUID,
    permission_ids: list[uuid.UUID] = Body(..., embed=True),
    current_user: dict = Depends(require_permission("account", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Set permissions for a role (replaces existing). Accepts JSON body: {"permission_ids": [...]}"""
    svc = AccountService(db, current_user["customer_id"])
    return await svc.set_role_permissions(role_id, permission_ids)

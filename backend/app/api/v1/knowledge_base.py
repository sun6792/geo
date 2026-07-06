"""Knowledge Base API endpoints — categories, assets, versions, search."""

import uuid

from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.core.pagination import PaginationParams, PaginatedResponse
from app.schemas.knowledge_base import (
    CategoryCreate, CategoryUpdate, CategoryResponse,
    AssetCreate, AssetUpdate, AssetResponse, AssetVersionResponse,
)
from app.services.knowledge_base_service import KnowledgeBaseService

router = APIRouter(tags=["Knowledge Base"])


# ── Categories ───────────────────────────────────────────────────

@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all KB categories (tree structure)."""
    svc = KnowledgeBaseService(db, current_user["customer_id"])
    return await svc.list_categories()


@router.post("/categories", response_model=CategoryResponse, status_code=201)
async def create_category(
    body: CategoryCreate,
    current_user: dict = Depends(require_permission("kb", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a KB category."""
    svc = KnowledgeBaseService(db, current_user["customer_id"])
    return await svc.create_category(
        name=body.name, slug=body.slug, parent_id=body.parent_id,
        description=body.description, created_by=current_user["user_id"],
    )


@router.patch("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: uuid.UUID,
    body: CategoryUpdate,
    current_user: dict = Depends(require_permission("kb", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a KB category."""
    svc = KnowledgeBaseService(db, current_user["customer_id"])
    return await svc.update_category(category_id, **body.model_dump(exclude_unset=True))


@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: uuid.UUID,
    current_user: dict = Depends(require_permission("kb", "delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a KB category."""
    svc = KnowledgeBaseService(db, current_user["customer_id"])
    await svc.delete_category(category_id)
    return {"message": "Category deleted"}


# ── Assets ───────────────────────────────────────────────────────

@router.get("/assets", response_model=PaginatedResponse[AssetResponse])
async def list_assets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    asset_type: str = Query(None),
    status: str = Query(None),
    category_id: uuid.UUID = Query(None),
    search: str = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List KB assets with filtering and pagination."""
    svc = KnowledgeBaseService(db, current_user["customer_id"])
    pagination = PaginationParams(page=page, page_size=page_size)
    items, total = await svc.list_assets(pagination, asset_type, status, category_id, search)
    return PaginatedResponse.create(items, total, pagination)


@router.post("/assets", response_model=AssetResponse, status_code=201)
async def create_asset(
    body: AssetCreate,
    current_user: dict = Depends(require_permission("kb", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new KB asset."""
    svc = KnowledgeBaseService(db, current_user["customer_id"])
    data = body.model_dump()
    data["created_by"] = current_user["user_id"]
    return await svc.create_asset(data)


@router.get("/assets/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific KB asset."""
    svc = KnowledgeBaseService(db, current_user["customer_id"])
    return await svc.get_asset(asset_id)


@router.patch("/assets/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: uuid.UUID,
    body: AssetUpdate,
    current_user: dict = Depends(require_permission("kb", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a KB asset (creates new version)."""
    svc = KnowledgeBaseService(db, current_user["customer_id"])
    data = body.model_dump(exclude_unset=True)
    data["updated_by"] = current_user["user_id"]
    return await svc.update_asset(asset_id, data)


@router.delete("/assets/{asset_id}")
async def archive_asset(
    asset_id: uuid.UUID,
    current_user: dict = Depends(require_permission("kb", "delete")),
    db: AsyncSession = Depends(get_db),
):
    """Archive a KB asset."""
    svc = KnowledgeBaseService(db, current_user["customer_id"])
    await svc.archive_asset(asset_id)
    return {"message": "Asset archived"}


@router.get("/assets/{slug}/versions", response_model=list[AssetVersionResponse])
async def get_asset_versions(
    slug: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get version history for an asset by slug."""
    svc = KnowledgeBaseService(db, current_user["customer_id"])
    return await svc.get_asset_versions(slug)

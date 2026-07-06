"""Content creation API endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.core.pagination import PaginationParams, PaginatedResponse
from app.schemas.content import (
    ContentBriefCreate, ContentBriefUpdate, ContentBriefResponse,
    ContentDraftResponse, ContentTemplateCreate, ContentTemplateResponse,
    GenerateRequest,
)
from app.services.content_service import ContentService

router = APIRouter(tags=["Content"])


# ── Briefs ───────────────────────────────────────────────────────

@router.get("/briefs", response_model=PaginatedResponse[ContentBriefResponse])
async def list_briefs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List content briefs."""
    svc = ContentService(db, current_user["customer_id"])
    pagination = PaginationParams(page=page, page_size=page_size)
    items, total = await svc.list_briefs(pagination, status)
    return PaginatedResponse.create(items, total, pagination)


@router.post("/briefs", response_model=ContentBriefResponse, status_code=201)
async def create_brief(
    body: ContentBriefCreate,
    current_user: dict = Depends(require_permission("content", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a content brief (must include KB source assets)."""
    svc = ContentService(db, current_user["customer_id"])
    data = body.model_dump()
    data["created_by"] = current_user["user_id"]
    return await svc.create_brief(data)


@router.get("/briefs/{brief_id}", response_model=ContentBriefResponse)
async def get_brief(
    brief_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific content brief."""
    svc = ContentService(db, current_user["customer_id"])
    return await svc.get_brief(brief_id)


@router.patch("/briefs/{brief_id}", response_model=ContentBriefResponse)
async def update_brief(
    brief_id: uuid.UUID,
    body: ContentBriefUpdate,
    current_user: dict = Depends(require_permission("content", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a content brief."""
    svc = ContentService(db, current_user["customer_id"])
    return await svc.update_brief(brief_id, body.model_dump(exclude_unset=True))


# ── AI Generation ────────────────────────────────────────────────

@router.post("/briefs/{brief_id}/generate")
async def generate_content(
    brief_id: uuid.UUID,
    body: GenerateRequest = GenerateRequest(),
    current_user: dict = Depends(require_permission("content", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Trigger AI content generation for a brief."""
    from app.services.generation_service import GenerationService
    svc = GenerationService(db, current_user["customer_id"])
    return await svc.generate(brief_id, current_user["user_id"], body.model_provider, body.model_name)


# ── Drafts ───────────────────────────────────────────────────────

@router.get("/drafts", response_model=list[ContentDraftResponse])
async def list_drafts(
    brief_id: uuid.UUID = Query(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List drafts for a brief."""
    svc = ContentService(db, current_user["customer_id"])
    return await svc.list_drafts(brief_id)


@router.get("/drafts/{draft_id}", response_model=ContentDraftResponse)
async def get_draft(
    draft_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific draft."""
    svc = ContentService(db, current_user["customer_id"])
    return await svc.get_draft(draft_id)


@router.patch("/drafts/{draft_id}", response_model=ContentDraftResponse)
async def update_draft(
    draft_id: uuid.UUID,
    body: dict,
    current_user: dict = Depends(require_permission("content", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Edit a draft manually."""
    svc = ContentService(db, current_user["customer_id"])
    return await svc.update_draft(draft_id, body)


# ── Templates ────────────────────────────────────────────────────

@router.get("/templates", response_model=list[ContentTemplateResponse])
async def list_templates(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List content templates."""
    svc = ContentService(db, current_user["customer_id"])
    return await svc.list_templates()


@router.post("/templates", response_model=ContentTemplateResponse, status_code=201)
async def create_template(
    body: ContentTemplateCreate,
    current_user: dict = Depends(require_permission("content", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a content template."""
    svc = ContentService(db, current_user["customer_id"])
    data = body.model_dump()
    data["created_by"] = current_user["user_id"]
    return await svc.create_template(data)

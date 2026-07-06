"""Publishing API endpoints — channels, schedules, records, performance."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.core.pagination import PaginationParams, PaginatedResponse
from app.services.publish_service import PublishService

router = APIRouter(tags=["Publish"])


# ── Channels ─────────────────────────────────────────────────────

@router.get("/channels")
async def list_channels(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List publishing channels."""
    svc = PublishService(db, current_user["customer_id"])
    return await svc.list_channels()


@router.post("/channels", status_code=201)
async def create_channel(
    body: dict,
    current_user: dict = Depends(require_permission("publish", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a publishing channel."""
    svc = PublishService(db, current_user["customer_id"])
    body["created_by"] = current_user["user_id"]
    return await svc.create_channel(body)


@router.patch("/channels/{channel_id}")
async def update_channel(
    channel_id: uuid.UUID,
    body: dict,
    current_user: dict = Depends(require_permission("publish", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a publishing channel."""
    svc = PublishService(db, current_user["customer_id"])
    return await svc.update_channel(channel_id, body)


@router.delete("/channels/{channel_id}")
async def delete_channel(
    channel_id: uuid.UUID,
    current_user: dict = Depends(require_permission("publish", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a publishing channel."""
    svc = PublishService(db, current_user["customer_id"])
    await svc.delete_channel(channel_id)
    return {"message": "Channel deleted"}


# ── Schedules ────────────────────────────────────────────────────

@router.get("/schedules")
async def list_schedules(
    status: str = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List publish schedules."""
    svc = PublishService(db, current_user["customer_id"])
    return await svc.list_schedules(status)


@router.post("/schedules", status_code=201)
async def schedule_publish(
    body: dict,
    current_user: dict = Depends(require_permission("publish", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Schedule a publish. Content must be fully approved."""
    svc = PublishService(db, current_user["customer_id"])
    scheduled_at = datetime.fromisoformat(body["scheduled_at"]) if body.get("scheduled_at") else datetime.now(timezone.utc)
    return await svc.schedule_publish(
        draft_id=uuid.UUID(body["draft_id"]),
        channel_id=uuid.UUID(body["channel_id"]),
        scheduled_at=scheduled_at,
        created_by=current_user["user_id"],
    )


@router.post("/schedules/{schedule_id}/publish-now")
async def publish_now(
    schedule_id: uuid.UUID,
    body: dict | None = None,
    current_user: dict = Depends(require_permission("publish", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Execute a publish immediately."""
    svc = PublishService(db, current_user["customer_id"])
    return await svc.publish_now(schedule_id, current_user["user_id"], (body or {}).get("published_url"))


@router.delete("/schedules/{schedule_id}")
async def cancel_schedule(
    schedule_id: uuid.UUID,
    current_user: dict = Depends(require_permission("publish", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a publish schedule."""
    svc = PublishService(db, current_user["customer_id"])
    await svc.cancel_schedule(schedule_id)
    return {"message": "Schedule cancelled"}


# ── Performance ──────────────────────────────────────────────────

@router.get("/performance", response_model=PaginatedResponse)
async def list_performance(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    draft_id: uuid.UUID = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List performance records."""
    svc = PublishService(db, current_user["customer_id"])
    pagination = PaginationParams(page=page, page_size=page_size)
    items, total = await svc.list_performance(pagination, draft_id)
    return PaginatedResponse.create(items, total, pagination)


@router.post("/performance", status_code=201)
async def record_performance(
    body: dict,
    current_user: dict = Depends(require_permission("publish", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Record performance metrics manually."""
    svc = PublishService(db, current_user["customer_id"])
    body["recorded_by"] = current_user["user_id"]
    return await svc.record_performance(body)

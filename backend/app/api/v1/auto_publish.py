"""P2 Auto-Publish API — channel management, auto-publish, retry, directional publishing."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.services.auto_publish_service import AutoPublishService

router = APIRouter(tags=["P2: Auto Publish"])


@router.get("/channel-types")
async def list_channel_types(current_user: dict = Depends(get_current_user)):
    """List all supported channel adapter types."""
    # This doesn't need DB, it's static
    from app.integrations.publish.base import ADAPTER_REGISTRY
    return [{"type": ct, "name": cls(None).channel_name, "target_model": cls(None).target_model}
            for ct, cls in ADAPTER_REGISTRY.items()]


@router.post("/channels/{channel_id}/bind")
async def bind_channel(channel_id: uuid.UUID, body: dict,
    current_user: dict = Depends(require_permission("publish", "update")), db: AsyncSession = Depends(get_db)):
    """Bind API credentials to a publish channel."""
    svc = AutoPublishService(db, current_user["customer_id"])
    return await svc.bind_channel(channel_id, body)


@router.post("/channels/{channel_id}/validate")
async def validate_channel(channel_id: uuid.UUID,
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Validate channel API credentials."""
    svc = AutoPublishService(db, current_user["customer_id"])
    return await svc.validate_channel_auth(channel_id)


@router.post("/auto-publish")
async def auto_publish(body: dict,
    current_user: dict = Depends(require_permission("publish", "create")), db: AsyncSession = Depends(get_db)):
    """Auto-publish a draft to multiple channels simultaneously.

    Body: {
        "draft_id": "uuid",
        "channel_ids": ["uuid1", "uuid2"],
        "scheduled_at": "2026-07-10T09:00:00Z"  // optional, for scheduled publishing
    }
    """
    svc = AutoPublishService(db, current_user["customer_id"])
    scheduled_at = None
    if body.get("scheduled_at"):
        scheduled_at = datetime.fromisoformat(body["scheduled_at"].replace("Z", "+00:00"))
    return await svc.auto_publish(
        draft_id=uuid.UUID(body["draft_id"]),
        channel_ids=[uuid.UUID(cid) for cid in body["channel_ids"]],
        published_by=current_user["user_id"],
        scheduled_at=scheduled_at,
    )


@router.post("/schedules/{schedule_id}/retry")
async def retry_publish(schedule_id: uuid.UUID,
    current_user: dict = Depends(require_permission("publish", "create")), db: AsyncSession = Depends(get_db)):
    """Retry a failed publish."""
    svc = AutoPublishService(db, current_user["customer_id"])
    return await svc.retry_publish(schedule_id, current_user["user_id"])


@router.get("/recommended-channels/{draft_id}")
async def get_recommended_channels(draft_id: uuid.UUID,
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get recommended channels for a draft based on content type and model targeting."""
    svc = AutoPublishService(db, current_user["customer_id"])
    return await svc.get_recommended_channels(draft_id)

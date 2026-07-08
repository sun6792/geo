"""P6: Agent 4 Enhanced Publishing API — smart distribution + channel matrix + analytics."""

import uuid
from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.services.publish_enhancements.smart_distribution import SmartDistributionEngine

router = APIRouter(prefix="/publish/smart", tags=["Smart Publish"])


# ════════════════════════════════════════════════════════════════
# Channel matrix
# ════════════════════════════════════════════════════════════════

@router.post("/channels/seed-matrix")
async def seed_channel_matrix(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Seed the three-tier channel matrix for the current customer.

    Creates 17 predefined channels across tier-1/2/3 with proper
    model targeting and weight configuration.
    Idempotent — safe to call multiple times.
    """
    engine = SmartDistributionEngine(db, current_user["customer_id"])
    result = await engine.seed_channel_matrix(current_user["user_id"])
    return {
        "message": f"渠道矩阵初始化完成: 新建{result['created']}个, 更新{result['updated']}个",
        **result,
    }


@router.get("/channels/matrix")
async def get_channel_matrix(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get the three-tier channel matrix for the current customer."""
    engine = SmartDistributionEngine(db, current_user["customer_id"])
    return await engine.get_channel_matrix()


# ════════════════════════════════════════════════════════════════
# Smart content-to-channel matching
# ════════════════════════════════════════════════════════════════

@router.get("/match-channels/{content_id}")
async def match_channels_for_content(
    content_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Smart match: which channels should this content be published to?

    Based on content's target_model, content_type, and channel matrix:
    - Model-specific content → tier-2 model channels
    - All content → tier-1 universal channels
    - Optional → tier-3 industry channels

    Returns ranked primary/secondary/optional channel lists.
    """
    engine = SmartDistributionEngine(db, current_user["customer_id"])
    return await engine.match_channels_for_content(content_id)


# ════════════════════════════════════════════════════════════════
# Daily publish quota (精品少稿)
# ════════════════════════════════════════════════════════════════

@router.get("/daily-quota")
async def check_daily_quota(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Check remaining daily publish quota.

    Enforces 精品少稿 strategy:
    - Max 2 depth articles/day
    - Max 5 derivative publications/day
    """
    engine = SmartDistributionEngine(db, current_user["customer_id"])
    return await engine.check_daily_publish_quota()


# ════════════════════════════════════════════════════════════════
# Smart publish
# ════════════════════════════════════════════════════════════════

@router.post("/publish-derivative/{derivative_id}")
async def smart_publish_derivative(
    derivative_id: uuid.UUID,
    scheduled_at: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Smart publish a content derivative to its matched channels.

    1. Checks daily quota
    2. Auto-matches best channels based on content model affinity
    3. Publishes to top 3 matched channels
    4. Enforces 精品少稿 limits
    """
    engine = SmartDistributionEngine(db, current_user["customer_id"])
    results = await engine.smart_publish_derivative(
        derivative_id, current_user["user_id"], scheduled_at
    )

    success_count = sum(1 for r in results if r.get("status") in ("published", "scheduled"))
    return {
        "derivative_id": str(derivative_id),
        "published_to": len(results),
        "successful": success_count,
        "results": results,
    }


# ════════════════════════════════════════════════════════════════
# Analytics
# ════════════════════════════════════════════════════════════════

@router.get("/analytics")
async def get_publish_analytics(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get per-channel publishing analytics.

    Returns publish counts and success rates by channel tier.
    """
    engine = SmartDistributionEngine(db, current_user["customer_id"])
    return await engine.get_channel_analytics(days)

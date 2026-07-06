"""Agent 5: Weekly Review & GEO Rules API."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.core.pagination import PaginationParams, PaginatedResponse
from app.schemas.agent import (
    WeeklyReviewResponse, GeoRuleResponse, GeoRuleUpdate,
)
from app.services.review_agent_service import ReviewAgentService

router = APIRouter(tags=["Agent 5: Weekly Review & Rules"])


# ── Weekly Reviews ───────────────────────────────────────────────

@router.get("/reviews", response_model=PaginatedResponse[WeeklyReviewResponse])
async def list_weekly_reviews(
    page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    svc = ReviewAgentService(db, current_user["customer_id"])
    items, total = await svc.list_weekly_reviews(PaginationParams(page=page, page_size=page_size))
    return PaginatedResponse.create(items, total, PaginationParams(page=page, page_size=page_size))


@router.get("/reviews/latest", response_model=WeeklyReviewResponse)
async def get_latest_review(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    svc = ReviewAgentService(db, current_user["customer_id"])
    result = await svc.get_latest_review()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No weekly review found")
    return result


@router.get("/reviews/{review_id}", response_model=WeeklyReviewResponse)
async def get_weekly_review(review_id: uuid.UUID,
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await ReviewAgentService(db, current_user["customer_id"]).get_weekly_review(review_id)


@router.post("/reviews/generate", response_model=WeeklyReviewResponse, status_code=201)
async def generate_weekly_review(
    current_user: dict = Depends(require_permission("review", "create")), db: AsyncSession = Depends(get_db),
):
    svc = ReviewAgentService(db, current_user["customer_id"])
    return await svc.generate_weekly_review(current_user["user_id"])


@router.get("/reviews/{review_id}/metrics")
async def get_review_metrics(review_id: uuid.UUID,
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await ReviewAgentService(db, current_user["customer_id"]).get_review_metrics(review_id)


# ── GEO Rules ────────────────────────────────────────────────────

@router.get("/rules", response_model=list[GeoRuleResponse])
async def list_rules(model_name: str = Query(None),
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await ReviewAgentService(db, current_user["customer_id"]).list_rules(model_name)


@router.patch("/rules/{rule_id}", response_model=GeoRuleResponse)
async def update_rule(rule_id: uuid.UUID, body: GeoRuleUpdate,
    current_user: dict = Depends(require_permission("rule", "update")), db: AsyncSession = Depends(get_db)):
    data = body.model_dump(exclude_unset=True)
    data["updated_by"] = current_user["user_id"]
    return await ReviewAgentService(db, current_user["customer_id"]).update_rule(rule_id, data)


@router.get("/rules/{rule_id}/versions", response_model=list[GeoRuleResponse])
async def get_rule_versions(rule_id: uuid.UUID,
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await ReviewAgentService(db, current_user["customer_id"]).get_rule_versions(rule_id)

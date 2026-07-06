"""Review workflow API endpoints — dual-review with hard gate."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.schemas.review import (
    AdvanceToClientRequest, ReviewActionRequest, ReviewCommentCreate,
    ReviewRecordResponse, ReviewCommentResponse, ChecklistItemResponse,
)
from app.services.review_service import ReviewService

router = APIRouter(tags=["Review"])


# ── Review Records ───────────────────────────────────────────────

@router.get("/", response_model=list[ReviewRecordResponse])
async def list_reviews(
    stage: str = Query(None),
    status: str = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List review records."""
    svc = ReviewService(db, current_user["customer_id"])
    return await svc.list_reviews(stage, status)


@router.get("/{review_id}", response_model=ReviewRecordResponse)
async def get_review(
    review_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific review record."""
    svc = ReviewService(db, current_user["customer_id"])
    return await svc.get_review(review_id)


# ── Submit & Advance ─────────────────────────────────────────────

@router.post("/drafts/{draft_id}/submit")
async def submit_for_review(
    draft_id: uuid.UUID,
    current_user: dict = Depends(require_permission("review", "comment")),
    db: AsyncSession = Depends(get_db),
):
    """Submit a draft for internal review."""
    svc = ReviewService(db, current_user["customer_id"])
    record = await svc.submit_for_internal_review(draft_id, current_user["user_id"])
    return {"review_id": str(record.id), "stage": record.stage, "status": record.status}


@router.post("/drafts/{draft_id}/advance-to-client")
async def advance_to_client(
    draft_id: uuid.UUID,
    body: AdvanceToClientRequest,
    current_user: dict = Depends(require_permission("review", "approve")),
    db: AsyncSession = Depends(get_db),
):
    """Advance to client review stage (HARD GATE: internal must be approved)."""
    svc = ReviewService(db, current_user["customer_id"])
    record = await svc.advance_to_client_review(
        draft_id, current_user["user_id"], body.client_email, body.client_name
    )
    return {
        "review_id": str(record.id),
        "stage": record.stage,
        "client_access_token": record.client_access_token,
        "client_review_url": f"/review/client/{record.client_access_token}",
    }


# ── Review Actions ───────────────────────────────────────────────

@router.post("/{review_id}/approve")
async def approve_review(
    review_id: uuid.UUID,
    body: ReviewActionRequest = ReviewActionRequest(),
    current_user: dict = Depends(require_permission("review", "approve")),
    db: AsyncSession = Depends(get_db),
):
    """Approve a review stage."""
    svc = ReviewService(db, current_user["customer_id"])
    record = await svc.approve(review_id, current_user["user_id"], "internal_user", body.comment)
    return {"status": record.status, "message": "Review approved"}


@router.post("/{review_id}/reject")
async def reject_review(
    review_id: uuid.UUID,
    body: ReviewActionRequest = ReviewActionRequest(),
    current_user: dict = Depends(require_permission("review", "approve")),
    db: AsyncSession = Depends(get_db),
):
    """Reject a review stage."""
    svc = ReviewService(db, current_user["customer_id"])
    record = await svc.reject(review_id, current_user["user_id"], "internal_user", body.comment)
    return {"status": record.status, "message": "Review rejected"}


@router.post("/{review_id}/request-changes")
async def request_changes(
    review_id: uuid.UUID,
    body: ReviewActionRequest = ReviewActionRequest(),
    current_user: dict = Depends(require_permission("review", "approve")),
    db: AsyncSession = Depends(get_db),
):
    """Request changes for a review stage."""
    svc = ReviewService(db, current_user["customer_id"])
    record = await svc.request_changes(review_id, current_user["user_id"], "internal_user", body.comment)
    return {"status": record.status, "message": "Changes requested"}


# ── Comments ─────────────────────────────────────────────────────

@router.post("/{review_id}/comments", response_model=ReviewCommentResponse, status_code=201)
async def add_comment(
    review_id: uuid.UUID,
    body: ReviewCommentCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a comment to a review."""
    svc = ReviewService(db, current_user["customer_id"])
    return await svc.add_comment(
        review_id=review_id,
        created_by=current_user["user_id"],
        comment_text=body.comment_text,
        comment_type=body.comment_type,
        parent_id=body.parent_id,
        selection_start=body.selection_start,
        selection_end=body.selection_end,
        selected_text=body.selected_text,
    )


@router.patch("/comments/{comment_id}/resolve", response_model=ReviewCommentResponse)
async def resolve_comment(
    comment_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a review comment as resolved."""
    svc = ReviewService(db, current_user["customer_id"])
    return await svc.resolve_comment(comment_id, current_user["user_id"])


# ── Checklists ───────────────────────────────────────────────────

@router.get("/checklists/{stage}", response_model=list[ChecklistItemResponse])
async def get_checklists(
    stage: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get review checklist items for a stage."""
    svc = ReviewService(db, current_user["customer_id"])
    return await svc.get_checklists(stage)

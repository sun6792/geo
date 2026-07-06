"""Public client review endpoint — accessed via secure token, no login required."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.review import ReviewRecordResponse, ReviewActionRequest, ReviewCommentCreate, ReviewCommentResponse
from app.services.review_service import ReviewService

router = APIRouter(tags=["Client Review (Public)"])


@router.get("/review/{token}", response_model=ReviewRecordResponse)
async def get_client_review(token: str, db: AsyncSession = Depends(get_db)):
    """Load the client review page via a secure access token. No login required."""
    try:
        # We need to extract customer_id from the token somehow
        # For now, we look up the review by token directly
        from sqlalchemy import select
        from app.models.review import ReviewRecord as RR
        result = await db.execute(
            select(RR.customer_id).where(RR.client_access_token == token).limit(1)
        )
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid review token")
        customer_id = row
        svc = ReviewService(db, customer_id)
        return await svc.get_review_by_token(token)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/review/{token}/approve")
async def client_approve(token: str, body: ReviewActionRequest = ReviewActionRequest(), db: AsyncSession = Depends(get_db)):
    """Client approves the content."""
    from sqlalchemy import select
    from app.models.review import ReviewRecord as RR
    result = await db.execute(
        select(RR).where(RR.client_access_token == token, RR.stage == "client_review").limit(1)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid review token")

    svc = ReviewService(db, record.customer_id)
    await svc.approve(record.id, uuid.UUID("00000000-0000-0000-0000-000000000000"), "client", body.comment)
    return {"status": "approved", "message": "审核已通过"}


@router.post("/review/{token}/reject")
async def client_reject(token: str, body: ReviewActionRequest = ReviewActionRequest(), db: AsyncSession = Depends(get_db)):
    """Client rejects the content."""
    from sqlalchemy import select
    from app.models.review import ReviewRecord as RR
    result = await db.execute(
        select(RR).where(RR.client_access_token == token, RR.stage == "client_review").limit(1)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid review token")

    svc = ReviewService(db, record.customer_id)
    await svc.reject(record.id, uuid.UUID("00000000-0000-0000-0000-000000000000"), "client", body.comment)
    return {"status": "rejected", "message": "审核已驳回"}


@router.post("/review/{token}/comments", response_model=ReviewCommentResponse)
async def client_add_comment(token: str, body: ReviewCommentCreate, db: AsyncSession = Depends(get_db)):
    """Client adds a comment."""
    from sqlalchemy import select
    from app.models.review import ReviewRecord as RR
    result = await db.execute(
        select(RR).where(RR.client_access_token == token, RR.stage == "client_review").limit(1)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid review token")

    svc = ReviewService(db, record.customer_id)
    return await svc.add_comment(
        review_id=record.id,
        created_by=uuid.UUID("00000000-0000-0000-0000-000000000000"),
        comment_text=body.comment_text,
        comment_type=body.comment_type,
        parent_id=body.parent_id,
        selection_start=body.selection_start,
        selection_end=body.selection_end,
        selected_text=body.selected_text,
    )

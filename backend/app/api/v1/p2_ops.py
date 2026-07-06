"""P2 Batch Operations, Monitoring, and Customer Portal APIs."""

import uuid
from datetime import datetime, timezone as tz

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.core.pagination import PaginationParams, PaginatedResponse
from app.services.batch_service import BatchService, MonitoringService

router = APIRouter(tags=["P2: Ops & Portal"])


# ══════════════════════════════════════════════════════════════
# Batch Operations
# ══════════════════════════════════════════════════════════════

@router.post("/batch/import/kb-assets")
async def import_kb_assets(body: dict,
    current_user: dict = Depends(require_permission("kb", "create")), db: AsyncSession = Depends(get_db)):
    """Batch import KB assets from Excel-parsed rows."""
    svc = BatchService(db, current_user["customer_id"])
    return await svc.import_kb_assets_from_excel(body.get("rows", []), current_user["user_id"])


@router.post("/batch/submit-review")
async def bulk_submit_review(body: dict,
    current_user: dict = Depends(require_permission("review", "approve")), db: AsyncSession = Depends(get_db)):
    """Submit multiple drafts for review."""
    svc = BatchService(db, current_user["customer_id"])
    draft_ids = [uuid.UUID(did) for did in body.get("draft_ids", [])]
    return await svc.bulk_submit_review(draft_ids, current_user["user_id"])


@router.get("/export/{resource_type}")
async def export_data(resource_type: str, asset_type: str = Query(None), model_name: str = Query(None),
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Export data for a resource type (kb_assets, detection_results, diagnosis_reports, publish_records)."""
    svc = BatchService(db, current_user["customer_id"])
    filters = {}
    if asset_type:
        filters["asset_type"] = asset_type
    if model_name:
        filters["model_name"] = model_name
    return await svc.export_data(resource_type, filters)


# ══════════════════════════════════════════════════════════════
# System Monitoring
# ══════════════════════════════════════════════════════════════

@router.get("/monitor/health")
async def system_health(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """System-wide health check for all components (auth required)."""
    svc = MonitoringService(db)
    return await svc.get_system_health()


@router.get("/monitor/tasks")
async def task_stats(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get background task statistics."""
    svc = MonitoringService(db, current_user["customer_id"])
    return await svc.get_task_stats()


@router.get("/monitor/usage")
async def usage_stats(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get resource usage statistics for the current customer."""
    svc = MonitoringService(db, current_user["customer_id"])
    return await svc.get_usage_stats()


@router.get("/operation-logs", response_model=PaginatedResponse)
async def list_operation_logs(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    user_id: uuid.UUID = Query(None), resource_type: str = Query(None),
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    """Query operation audit logs with filters."""
    svc = MonitoringService(db, current_user["customer_id"])
    pagination = PaginationParams(page=page, page_size=page_size)
    items, total = await svc.get_operation_logs(pagination, user_id, resource_type)
    return PaginatedResponse.create(items, total, pagination)


# ══════════════════════════════════════════════════════════════
# Customer Self-Service Portal
# ══════════════════════════════════════════════════════════════

@router.get("/portal/{token}/dashboard")
async def client_dashboard(token: str, db: AsyncSession = Depends(get_db)):
    """Client self-service dashboard accessed via secure token."""
    from app.models.review import ReviewRecord
    from sqlalchemy import select
    result = await db.execute(
        select(ReviewRecord).where(
            ReviewRecord.client_access_token == token,
            ReviewRecord.client_token_expires > datetime.now(tz.utc),
        ).limit(1)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid or expired portal token")

    # Aggregate available data for this customer
    svc = MonitoringService(db, record.customer_id)
    usage = await svc.get_usage_stats()
    task_stats = await svc.get_task_stats()

    return {
        "customer_id": str(record.customer_id),
        "data_summary": usage,
        "review_status": record.status,
        "review_stage": record.stage,
    }


@router.get("/portal/{token}/reviews")
async def client_review_list(token: str, db: AsyncSession = Depends(get_db)):
    """List reviews for a client via portal token."""
    from app.models.review import ReviewRecord
    from app.models.content import ContentDraft
    from sqlalchemy import select

    result = await db.execute(
        select(ReviewRecord).where(
            ReviewRecord.client_access_token == token,
            ReviewRecord.client_token_expires > datetime.now(tz.utc),
        ).limit(1)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid or expired portal token")

    # Get all review records for this customer's client
    reviews_result = await db.execute(
        select(ReviewRecord, ContentDraft).join(
            ContentDraft, ContentDraft.id == ReviewRecord.draft_id
        ).where(
            ReviewRecord.customer_id == record.customer_id,
            ReviewRecord.client_reviewer_email == record.client_reviewer_email,
        ).order_by(ReviewRecord.created_at.desc()).limit(20)
    )

    items = []
    for rev, draft in reviews_result.all():
        items.append({
            "review_id": str(rev.id), "draft_id": str(rev.draft_id),
            "draft_title": draft.title, "stage": rev.stage,
            "status": rev.status, "reviewed_at": rev.reviewed_at.isoformat() if rev.reviewed_at else None,
        })
    return items

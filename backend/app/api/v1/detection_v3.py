"""P6: Agent 1 V3 API — async probe execution with BatchProbeScheduler."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.core.pagination import PaginationParams, PaginatedResponse
from app.integrations.llm_probe.scheduler import BatchProbeScheduler
from app.integrations.llm_probe.models import LLMProbeResult, ProbeTaskProgress
from app.integrations.llm_probe.factory import LLMProbeFactory

router = APIRouter(prefix="/detection/v3", tags=["Detection V3"])


@router.post("/tasks/{task_id}/run")
async def run_detection_v3(
    task_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    use_celery: bool = Query(False, description="Use Celery async task queue"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Execute a complete detection task using the new BatchProbeScheduler.

    Mode 1 (default): Run inline — returns when complete (~30-60 sec)
    Mode 2 (use_celery=true): Enqueue to Celery — returns immediately with task ID
    """
    # ── Check billing quota ────────────────────────────────────
    try:
        from app.services.billing_service import BillingService
        svc = BillingService(db, current_user["customer_id"])
        quota = await svc.check_quota("llm_probes")
        if not quota.get("available", True):
            raise HTTPException(status_code=429, detail="探测配额已用完，请联系管理员升级套餐")
    except HTTPException:
        raise
    except Exception:
        pass  # Billing not critical in dev mode

    if use_celery:
        try:
            from app.tasks.celery_probe import run_detection_task
            run_detection_task.delay(
                str(current_user["customer_id"]), str(task_id)
            )
            return {"task_id": str(task_id), "mode": "celery", "status": "enqueued"}
        except ImportError:
            raise HTTPException(status_code=503, detail="Celery not available")

    # ── Inline execution ───────────────────────────────────────
    scheduler = BatchProbeScheduler(db, current_user["customer_id"])
    result = await scheduler.execute_task(task_id)
    await db.commit()
    return result


@router.get("/tasks/{task_id}/progress")
async def get_task_progress(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get real-time progress of a detection task."""
    from sqlalchemy import select
    r = await db.execute(
        select(ProbeTaskProgress).where(
            ProbeTaskProgress.tenant_id == current_user["customer_id"],
            ProbeTaskProgress.task_id == task_id,
        ).order_by(ProbeTaskProgress.created_at.desc()).limit(1)
    )
    progress = r.scalar_one_or_none()
    if not progress:
        raise HTTPException(status_code=404, detail="No progress found for this task")

    return {
        "task_id": str(task_id),
        "total_queries": progress.total_queries,
        "completed": progress.completed_queries,
        "failed": progress.failed_queries,
        "skipped": progress.skipped_queries,
        "pct": round(progress.completed_queries / max(progress.total_queries, 1) * 100, 1),
        "model_progress": progress.model_progress,
        "started_at": progress.started_at.isoformat() if progress.started_at else None,
        "completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
    }


@router.get("/tasks/{task_id}/results")
async def get_probe_results(
    task_id: uuid.UUID,
    model_id: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get structured probe results for a task, with filters."""
    from sqlalchemy import func

    query = __import__('sqlalchemy').select(LLMProbeResult).where(
        LLMProbeResult.tenant_id == current_user["customer_id"],
        LLMProbeResult.task_id == task_id,
    )
    count_q = __import__('sqlalchemy').select(func.count(LLMProbeResult.id)).where(
        LLMProbeResult.tenant_id == current_user["customer_id"],
        LLMProbeResult.task_id == task_id,
    )
    if model_id:
        query = query.where(LLMProbeResult.model_id == model_id)
        count_q = count_q.where(LLMProbeResult.model_id == model_id)
    if status:
        query = query.where(LLMProbeResult.status == status)
        count_q = count_q.where(LLMProbeResult.status == status)

    total = (await db.execute(count_q)).scalar() or 0
    results = (await db.execute(
        query.order_by(LLMProbeResult.model_id, LLMProbeResult.probe_time)
        .offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    return {
        "task_id": str(task_id),
        "total": total, "page": page, "page_size": page_size,
        "results": [
            {
                "id": str(r.id), "model_id": r.model_id, "model_name": r.model_name,
                "query_text": r.query_text[:200], "query_type": r.query_type,
                "raw_answer": r.raw_answer[:500],
                "brand_mentioned": r.brand_mentioned, "brand_rank": r.brand_rank,
                "mentioned_competitors": r.mentioned_competitors,
                "has_error_info": r.has_error_info, "has_negative": r.has_negative,
                "info_consistency_score": r.info_consistency_score,
                "input_tokens": r.input_tokens, "output_tokens": r.output_tokens,
                "probe_duration_ms": r.probe_duration_ms,
                "status": r.status, "error_message": r.error_message,
                "probe_time": r.probe_time.isoformat() if r.probe_time else None,
            }
            for r in results
        ],
    }


@router.get("/available-models")
async def list_available_models():
    """List all configured LLM models with their status."""
    available = LLMProbeFactory.get_available_models()
    all_models = list(LLMProbeFactory.MODEL_REGISTRY.keys()) if hasattr(LLMProbeFactory, 'MODEL_REGISTRY') else []
    return {
        "available": available,
        "total_configured": len(available),
        "all_registered": all_models,
        "models": [
            {
                "model_id": m,
                "configured": m in available,
                "status": "ready" if m in available else "api_key_missing",
            }
            for m in all_models
        ],
    }

"""P6: Unified Pipeline Status API — single view of all 5 agent statuses.

Provides:
- Per-customer pipeline health overview
- Each agent's latest execution status + next action
- Frontend navigation hints
- Pipeline completion percentage
"""

import uuid
from datetime import datetime, timezone, date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.agent import DetectionTask, DetectionResult, DiagnosisReport, GeoRule
from app.models.content import ContentDraft, ContentBrief
from app.models.review import ReviewRecord
from app.models.publish import PublishRecord, PublishSchedule, WeeklyReview
from app.models.identity import BackflowRecord, EnterpriseIdentityProfile

router = APIRouter(prefix="/pipeline", tags=["Pipeline Status"])


@router.get("/status")
async def get_pipeline_status(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get the unified pipeline status for the current customer.

    Returns each agent's:
    - Status (not_started / in_progress / completed / needs_attention)
    - Latest execution info
    - Next action hint with navigation path
    - Counts and metrics
    """
    cid = current_user["customer_id"]
    now = datetime.now(timezone.utc)
    today = date.today()
    week_ago = now - timedelta(days=7)

    # ── Agent 1: Detection ────────────────────────────────────
    tasks = (await db.execute(
        select(DetectionTask).where(
            DetectionTask.customer_id == cid,
        ).order_by(desc(DetectionTask.created_at)).limit(5)
    )).scalars().all()

    active_tasks = [t for t in tasks if t.is_active]
    recent_results = (await db.execute(
        select(func.count(DetectionResult.id)).where(
            DetectionResult.customer_id == cid,
            DetectionResult.detected_at >= week_ago,
        )
    )).scalar() or 0

    has_identity = (await db.execute(
        select(func.count(EnterpriseIdentityProfile.id)).where(
            EnterpriseIdentityProfile.customer_id == cid,
        )
    )).scalar() or 0

    agent1 = {
        "status": "completed" if (tasks and tasks[0].last_status == "completed") else (
            "in_progress" if (tasks and tasks[0].last_status == "running") else (
                "not_started" if not tasks else "needs_attention"
            )
        ),
        "tasks_total": len(tasks),
        "tasks_active": len(active_tasks),
        "results_this_week": recent_results,
        "has_identity_profile": has_identity > 0,
        "latest_task": str(tasks[0].id) if tasks else None,
        "next_action": "创建探测任务" if not tasks else "查看探测结果",
        "next_path": "/detection" if not tasks else "/detection",
    }

    # ── Agent 2: Diagnosis ────────────────────────────────────
    diag_reports = (await db.execute(
        select(DiagnosisReport).where(
            DiagnosisReport.customer_id == cid,
        ).order_by(desc(DiagnosisReport.created_at)).limit(5)
    )).scalars().all()

    latest_diag = diag_reports[0] if diag_reports else None

    # Check gaps
    from app.services.layered_diagnosis.models import DiagnosisGap
    open_gaps = 0
    if latest_diag:
        open_gaps = (await db.execute(
            select(func.count(DiagnosisGap.id)).where(
                DiagnosisGap.customer_id == cid,
                DiagnosisGap.diagnosis_report_id == latest_diag.id,
                DiagnosisGap.status == "open",
            )
        )).scalar() or 0

    agent2 = {
        "status": "completed" if latest_diag else (
            "not_started" if not diag_reports else "needs_attention"
        ),
        "reports_total": len(diag_reports),
        "latest_report_id": str(latest_diag.id) if latest_diag else None,
        "latest_total_score": latest_diag.report_json.get("total_score") if latest_diag and latest_diag.report_json else None,
        "open_gaps": open_gaps,
        "next_action": "发起三层诊断" if not latest_diag else (
            f"查看{open_gaps}个未修复缺口" if open_gaps > 0 else "缺口已全部修复"
        ),
        "next_path": "/diagnosis",
    }

    # ── Agent 3: Content ──────────────────────────────────────
    drafts = (await db.execute(
        select(ContentDraft).where(
            ContentDraft.customer_id == cid,
        ).order_by(desc(ContentDraft.created_at)).limit(10)
    )).scalars().all()

    in_review_count = sum(1 for d in drafts if d.status == "in_review")
    approved_count = sum(1 for d in drafts if d.status == "approved")
    drafts_this_week = sum(1 for d in drafts if d.created_at and d.created_at >= week_ago)

    agent3 = {
        "status": "completed" if drafts else "not_started",
        "drafts_total": len(drafts),
        "drafts_this_week": drafts_this_week,
        "in_review": in_review_count,
        "approved": approved_count,
        "latest_draft_id": str(drafts[0].id) if drafts else None,
        "next_action": "查看内容草稿" if drafts else "从缺口生成内容",
        "next_path": "/content",
        "can_generate_from_gaps": open_gaps > 0,
    }

    # ── Agent 4: Review & Publish ─────────────────────────────
    pending_reviews = (await db.execute(
        select(func.count(ReviewRecord.id)).where(
            ReviewRecord.customer_id == cid,
            ReviewRecord.status == "pending",
        )
    )).scalar() or 0

    publishes_this_week = (await db.execute(
        select(func.count(PublishRecord.id)).where(
            PublishRecord.customer_id == cid,
            PublishRecord.published_at >= week_ago,
            PublishRecord.publish_status == "success",
        )
    )).scalar() or 0

    agent4 = {
        "status": "in_progress" if pending_reviews > 0 else (
            "completed" if publishes_this_week > 0 else "not_started"
        ),
        "pending_reviews": pending_reviews,
        "published_this_week": publishes_this_week,
        "next_action": f"处理{pending_reviews}条待审内容" if pending_reviews > 0 else (
            "查看发布记录" if publishes_this_week > 0 else "等待内容进入审核"
        ),
        "next_path": "/review" if pending_reviews > 0 else "/publish",
    }

    # ── Agent 5: Weekly Review ────────────────────────────────
    weekly = (await db.execute(
        select(WeeklyReview).where(
            WeeklyReview.customer_id == cid,
        ).order_by(desc(WeeklyReview.week_start)).limit(4)
    )).scalars().all()

    backflows_applied = (await db.execute(
        select(func.count(BackflowRecord.id)).where(
            BackflowRecord.customer_id == cid,
            BackflowRecord.applied == True,
        )
    )).scalar() or 0

    backflows_pending = (await db.execute(
        select(func.count(BackflowRecord.id)).where(
            BackflowRecord.customer_id == cid,
            BackflowRecord.applied == False,
        )
    )).scalar() or 0

    agent5 = {
        "status": "completed" if weekly else "not_started",
        "reviews_total": len(weekly),
        "latest_review_id": str(weekly[0].id) if weekly else None,
        "backflows_applied": backflows_applied,
        "backflows_pending": backflows_pending,
        "next_action": "查看周报复盘" if weekly else "生成首份周报",
        "next_path": "/weekly-review",
        "can_apply_backflow": backflows_pending > 0,
    }

    # ── Pipeline health ───────────────────────────────────────
    agents = [agent1, agent2, agent3, agent4, agent5]
    completed_agents = sum(1 for a in agents if a["status"] == "completed")
    in_progress_agents = sum(1 for a in agents if a["status"] == "in_progress")

    return {
        "customer_id": str(cid),
        "pipeline_health": {
            "overall_status": "running" if in_progress_agents > 0 else (
                "complete" if completed_agents >= 3 else "initializing"
            ),
            "completion_pct": completed_agents * 20,
            "agents_completed": completed_agents,
            "agents_in_progress": in_progress_agents,
            "total_backflows_applied": backflows_applied,
        },
        "agents": {
            "agent1_detection": agent1,
            "agent2_diagnosis": agent2,
            "agent3_content": agent3,
            "agent4_review_publish": agent4,
            "agent5_weekly_review": agent5,
        },
        "recommended_next_step": _recommend_next(agents, agent1, agent4, agent2, agent3, agent5),
    }


def _recommend_next(agents, a1, a4, a2, a3, a5):
    """Determine the recommended next step based on pipeline state."""
    if a1["status"] == "not_started":
        return {"action": "创建第一个探测任务", "path": "/detection",
                "why": "Agent1探测是所有后续环节的数据基础"}
    if a1["status"] == "completed" and a2["status"] == "not_started":
        return {"action": "发起三层诊断", "path": "/diagnosis",
                "why": "Agent1探测已完成，可基于探测数据做精准诊断"}
    if a2["open_gaps"] > 0 and len([a for a in agents if a["status"] == "completed"]) >= 2:
        return {"action": "从缺口生成内容", "path": "/content",
                "why": f"有{a2['open_gaps']}个待修复缺口，可一键生成内容"}
    if a4["pending_reviews"] > 0:
        return {"action": "处理待审核内容", "path": "/review",
                "why": f"有{a4['pending_reviews']}条内容等待审核"}
    if a5["status"] == "not_started":
        return {"action": "生成首份周报复盘", "path": "/weekly-review",
                "why": "发布数据已产生，可生成复盘报告查看效果"}
    return {"action": "查看管道总览", "path": "/dashboard",
            "why": "所有智能体已运行，系统持续自动化优化中"}

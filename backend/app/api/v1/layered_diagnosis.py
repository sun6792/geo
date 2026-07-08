"""P6: Agent 2 Layered Diagnosis API — three-layer diagnosis + gap checklist + Agent 3 linkage."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.services.layered_diagnosis import EnhancedDiagnosisService

router = APIRouter(prefix="/diagnosis/layered", tags=["Layered Diagnosis"])


# ════════════════════════════════════════════════════════════════
# Full diagnosis
# ════════════════════════════════════════════════════════════════

@router.post("/run")
async def run_layered_diagnosis(
    detection_task_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Execute complete three-layer diagnosis.

    Pulls all Agent 1 data and runs the full diagnostic pipeline:
    1. Identity trust verification analysis
    2. Three-layer asset diagnosis (basic/marketing/multimodal)
    3. DeepSeek-powered intelligent gap attribution
    4. Five-dimension scoring with historical comparison
    5. Precise gap checklist generation

    Returns complete diagnosis report with prioritized gaps.
    """
    service = EnhancedDiagnosisService(db, current_user["customer_id"])
    result = await service.run_full_diagnosis(
        generated_by=current_user["user_id"],
        detection_task_id=detection_task_id,
    )
    return result


# ════════════════════════════════════════════════════════════════
# Score trends
# ════════════════════════════════════════════════════════════════

@router.get("/trends")
async def get_score_trends(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get historical score trends with change tracking.

    Returns latest scores + 12-period trend data for radar/line charts.
    """
    service = EnhancedDiagnosisService(db, current_user["customer_id"])
    return await service.get_score_trends()


@router.get("/history")
async def get_score_history(
    limit: int = Query(12, ge=1, le=52),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get raw score history records."""
    service = EnhancedDiagnosisService(db, current_user["customer_id"])
    history = await service.get_score_history(limit)
    return {
        "total": len(history),
        "records": [
            {
                "id": str(h.id),
                "date": h.recorded_at.isoformat(),
                "total_score": h.total_score,
                "identity_score": h.identity_score,
                "basic_asset_score": h.basic_asset_score,
                "marketing_asset_score": h.marketing_asset_score,
                "multimodal_asset_score": h.multimodal_asset_score,
                "sentiment_score": h.sentiment_score,
                "urgent_gaps": h.urgent_gaps,
                "important_gaps": h.important_gaps,
                "total_score_change": h.total_score_change,
            }
            for h in history
        ],
    }


# ════════════════════════════════════════════════════════════════
# Gap checklist
# ════════════════════════════════════════════════════════════════

@router.get("/reports/{report_id}/gaps")
async def get_gap_checklist(
    report_id: uuid.UUID,
    layer: str | None = Query(None, description="Filter: basic/marketing/multimodal"),
    priority: str | None = Query(None, description="Filter: urgent/important/long_term"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get the gap checklist for a diagnosis report.

    Returns prioritized gaps with:
    - Layer classification (basic/marketing/multimodal)
    - Impact weight and explanation
    - Affected models
    - Fix recommendations
    - Content type needed for repair
    - Conversion status (whether already sent to Agent 3)
    """
    service = EnhancedDiagnosisService(db, current_user["customer_id"])
    gaps = await service.get_gap_checklist(report_id, layer, priority)

    return {
        "report_id": str(report_id),
        "total": len(gaps),
        "urgent": sum(1 for g in gaps if g.priority == "urgent"),
        "important": sum(1 for g in gaps if g.priority == "important"),
        "long_term": sum(1 for g in gaps if g.priority == "long_term"),
        "gaps": [
            {
                "id": str(g.id),
                "layer": g.layer,
                "category": g.category,
                "name": g.gap_name,
                "description": g.description,
                "impact_weight": g.impact_weight,
                "impact_explanation": g.impact_explanation,
                "affected_models": g.affected_models,
                "fix_recommendation": g.fix_recommendation,
                "content_type_needed": g.content_type_needed,
                "target_keywords": g.target_keywords,
                "estimated_impact": g.estimated_impact,
                "priority": g.priority,
                "priority_reason": g.priority_reason,
                "status": g.status,
                "converted_to_brief": g.converted_to_brief,
                "linked_brief_id": str(g.linked_brief_id) if g.linked_brief_id else None,
            }
            for g in gaps
        ],
    }


@router.patch("/gaps/{gap_id}")
async def update_gap(
    gap_id: uuid.UUID,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update a gap item (status change, priority adjustment, etc.).

    Body: {"status": "fixed", "priority": "urgent", ...}
    """
    service = EnhancedDiagnosisService(db, current_user["customer_id"])
    gap = await service.update_gap(gap_id, data)
    return {"id": str(gap.id), "status": gap.status, "priority": gap.priority}


@router.delete("/gaps/{gap_id}")
async def delete_gap(
    gap_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete a gap from the checklist."""
    service = EnhancedDiagnosisService(db, current_user["customer_id"])
    await service.delete_gap(gap_id)
    return {"deleted": True}


@router.post("/reports/{report_id}/gaps/manual")
async def add_manual_gap(
    report_id: uuid.UUID,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Manually add a gap to the checklist."""
    service = EnhancedDiagnosisService(db, current_user["customer_id"])
    gap = await service.add_manual_gap(report_id, data, current_user["user_id"])
    return {"id": str(gap.id), "name": gap.gap_name, "is_manual": True}


# ════════════════════════════════════════════════════════════════
# Gap → Brief conversion (Agent 2 → Agent 3 handoff)
# ════════════════════════════════════════════════════════════════

@router.post("/gaps/convert-to-briefs")
async def convert_gaps_to_briefs(
    gap_ids: list[uuid.UUID],
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """One-click: convert selected diagnosis gaps into Agent 3 ContentBriefs.

    Each gap gets a tailored content brief with:
    - Optimized title and keywords
    - Matched content type for the gap category
    - Priority-preserving scheduling
    - KB source requirements

    Body: [uuid1, uuid2, ...]
    Returns: list of created briefs with gap linkages.
    """
    service = EnhancedDiagnosisService(db, current_user["customer_id"])
    briefs = await service.convert_gaps_to_briefs(gap_ids, current_user["user_id"])
    return {
        "converted": len(briefs),
        "briefs": briefs,
        "message": f"已创建{len(briefs)}个内容创作Brief，可前往内容创作页面查看",
    }


# ════════════════════════════════════════════════════════════════
# Diagnosis rules (configurable)
# ════════════════════════════════════════════════════════════════

@router.get("/rules")
async def list_diagnosis_rules(
    industry: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List configurable diagnosis rules (global + industry-specific)."""
    service = EnhancedDiagnosisService(db, current_user["customer_id"])
    rules = await service.list_rules(industry)
    return {
        "total": len(rules),
        "rules": [
            {
                "id": str(r.id),
                "industry": r.industry,
                "rule_name": r.rule_name,
                "rule_category": r.rule_category,
                "layer": r.layer,
                "dimension": r.dimension,
                "weight": r.weight,
                "check_logic": r.check_logic,
                "severity_thresholds": r.severity_thresholds,
            }
            for r in rules
        ],
    }


# ════════════════════════════════════════════════════════════════
# Report management
# ════════════════════════════════════════════════════════════════

@router.get("/reports/{report_id}")
async def get_report_detail(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get a single layered diagnosis report with gaps."""
    from sqlalchemy import select
    from app.models.agent import DiagnosisReport
    from app.services.layered_diagnosis.models import DiagnosisGap

    r = await db.execute(select(DiagnosisReport).where(DiagnosisReport.id == report_id, DiagnosisReport.customer_id == current_user["customer_id"]))
    report = r.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    gaps_r = await db.execute(select(DiagnosisGap).where(DiagnosisGap.diagnosis_report_id == report_id))
    gaps = gaps_r.scalars().all()

    return {
        "id": str(report.id),
        "title": report.title,
        "report_type": report.report_type,
        "diagnosis_period_start": report.diagnosis_period_start.isoformat() if report.diagnosis_period_start else None,
        "diagnosis_period_end": report.diagnosis_period_end.isoformat() if report.diagnosis_period_end else None,
        "status": report.status,
        "summary": report.summary,
        "report_json": report.report_json,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "gaps_count": len(gaps),
        "gaps": [{"id": str(g.id), "layer": g.layer, "category": g.category, "name": g.gap_name, "description": g.description, "impact_weight": g.impact_weight, "priority": g.priority, "content_type_needed": g.content_type_needed, "affected_models": g.affected_models, "estimated_impact": g.estimated_impact, "converted_to_brief": g.converted_to_brief} for g in gaps],
    }


@router.delete("/reports/{report_id}")
async def delete_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete a diagnosis report and its gaps."""
    from sqlalchemy import delete
    from app.models.agent import DiagnosisReport
    from app.services.layered_diagnosis.models import DiagnosisGap

    # Delete gaps first
    await db.execute(delete(DiagnosisGap).where(DiagnosisGap.diagnosis_report_id == report_id, DiagnosisGap.customer_id == current_user["customer_id"]))
    # Delete report
    result = await db.execute(delete(DiagnosisReport).where(DiagnosisReport.id == report_id, DiagnosisReport.customer_id == current_user["customer_id"]))
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"deleted": True, "report_id": str(report_id)}

"""P6: Agent 5 Self-Evolution API — benchmarking + asset growth + backflow + rollback."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.services.self_evolution.evolution_engine import SelfEvolutionEngine

router = APIRouter(prefix="/weekly-review/evolution", tags=["Self Evolution"])


# ════════════════════════════════════════════════════════════════
# Competitor benchmarking
# ════════════════════════════════════════════════════════════════

@router.post("/benchmark/{review_id}")
async def run_competitor_benchmark(
    review_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Run multi-dimension competitor benchmarking for a weekly review.

    Compares: source count, asset volume, AI exposure, sentiment health.
    Generates overtaking strategy based on competitor weaknesses.
    """
    engine = SelfEvolutionEngine(db, current_user["customer_id"])
    results = await engine.benchmark_competitors(review_id)
    return {"review_id": str(review_id), "competitors_analyzed": len(results), "benchmarks": results}


# ════════════════════════════════════════════════════════════════
# Asset growth
# ════════════════════════════════════════════════════════════════

@router.post("/asset-growth/{review_id}")
async def assess_asset_growth(
    review_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Assess four-category asset growth with AI weight estimation.

    Tracks: identity trust, basic assets, marketing assets, multimodal assets.
    Estimates overall AI model weight gain.
    """
    engine = SelfEvolutionEngine(db, current_user["customer_id"])
    return await engine.assess_asset_growth(review_id)


# ════════════════════════════════════════════════════════════════
# Clarification tasks
# ════════════════════════════════════════════════════════════════

@router.post("/clarification-tasks/{review_id}")
async def generate_clarification_tasks(
    review_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Auto-generate clarification tasks from negative sentiment.

    Scans all negative/alert sentiment and creates:
    - BackflowRecords routed to Agent 3
    - ContentBrief records for clarification content
    """
    engine = SelfEvolutionEngine(db, current_user["customer_id"])
    tasks = await engine.generate_clarification_tasks(review_id)
    return {"tasks_created": len(tasks), "tasks": tasks}


# ════════════════════════════════════════════════════════════════
# Backflow application
# ════════════════════════════════════════════════════════════════

@router.post("/apply-backflow/{review_id}")
async def apply_backflow_strategies(
    review_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Apply pending backflow strategies to Agent 1-4 configs.

    This is the CLOSED LOOP:
    - keyword_optimization → Agent 1 (add to detection tasks)
    - model_targeting → Agent 1 (adjust model weights)
    - sentiment_alert → Agent 3 (create clarification content)
    - content_gap → Agent 3 (prioritize content types)
    - rule_update → Agent 2 (create/update diagnosis rules)
    - channel_optimization → Agent 4 (adjust channel weights)
    """
    engine = SelfEvolutionEngine(db, current_user["customer_id"])
    result = await engine.apply_backflow_strategies(review_id)
    return {
        "message": f"Applied {result['total_applied']} backflow strategies",
        **result,
    }


# ════════════════════════════════════════════════════════════════
# Intelligent report
# ════════════════════════════════════════════════════════════════

@router.post("/intelligent-report/{review_id}")
async def generate_intelligent_report(
    review_id: uuid.UUID,
    data_overview: dict = {},
    competitor_data: list = [],
    asset_growth: dict = {},
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Generate DeepSeek-powered strategic insights for a weekly review.

    Produces: executive summary, top wins/risks, competitor analysis,
    asset growth assessment, next week strategy (per-agent adjustments),
    clarification tasks.
    """
    engine = SelfEvolutionEngine(db, current_user["customer_id"])
    return await engine.generate_intelligent_report(
        review_id, data_overview, competitor_data, asset_growth
    )


# ════════════════════════════════════════════════════════════════
# Rule rollback
# ════════════════════════════════════════════════════════════════

@router.post("/rules/{rule_id}/rollback")
async def rollback_rule(
    rule_id: uuid.UUID,
    target_version: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Rollback a GEO rule to a previous version.

    Creates a new version with the content from the target version.
    Previous versions are preserved for audit trail.
    """
    engine = SelfEvolutionEngine(db, current_user["customer_id"])
    rule = await engine.rollback_rule(rule_id, target_version)
    return {
        "id": str(rule.id),
        "rule_name": rule.rule_name,
        "version": rule.version,
        "is_latest": rule.is_latest,
        "message": f"Rule rolled back — new version {rule.version} created from historical version",
    }

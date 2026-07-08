"""P6: Multi-Model Probe API endpoints — dedicated routes for five-model Q&A probing.

Adds endpoints under /api/v1/detection/probe for:
- Starting probe execution
- Querying execution status
- Retrieving raw responses + structured extractions
- Human correction of extraction results
- Statistics aggregation
- Report export
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.core.pagination import PaginationParams, PaginatedResponse
from app.models.account import User
from app.services.multi_model_probe import MultiModelProbeService

router = APIRouter(prefix="/detection/probe", tags=["Multi-Model Probe"])


# ════════════════════════════════════════════════════════════════
# Probe execution
# ════════════════════════════════════════════════════════════════

@router.post("/tasks/{task_id}/start")
async def start_probe(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start a multi-model probe execution for a detection task.

    Launches concurrent probing across all target models (豆包/文心/千问/元宝/星火).
    Each model receives model-specific persona prompts via DeepSeek API.
    Results are auto-parsed and persisted.
    """
    service = MultiModelProbeService(db, current_user.customer_id)
    execution = await service.start_probe(task_id)

    return {
        "execution_id": str(execution.id),
        "task_id": str(execution.task_id),
        "status": execution.status,
        "total_questions": execution.total_questions,
        "completed_questions": execution.completed_questions,
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
    }


@router.get("/tasks/{task_id}/status")
async def get_probe_status(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the current execution status of a probe task."""
    service = MultiModelProbeService(db, current_user.customer_id)
    execution = await service.get_execution(task_id)

    if not execution:
        raise HTTPException(status_code=404, detail="No probe execution found for this task")

    return {
        "execution_id": str(execution.id),
        "task_id": str(execution.task_id),
        "status": execution.status,
        "total_questions": execution.total_questions,
        "completed_questions": execution.completed_questions,
        "successful_questions": execution.successful_questions,
        "failed_questions": execution.failed_questions,
        "retried_questions": execution.retried_questions,
        "total_duration_ms": execution.total_duration_ms,
        "avg_latency_ms": execution.avg_latency_ms,
        "max_latency_ms": execution.max_latency_ms,
        "model_progress": execution.model_progress,
        "errors": execution.errors[-20:],  # Latest 20 errors
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
    }


# ════════════════════════════════════════════════════════════════
# Raw responses
# ════════════════════════════════════════════════════════════════

@router.get("/tasks/{task_id}/responses")
async def list_raw_responses(
    task_id: uuid.UUID,
    model_name: str | None = Query(None, description="Filter by model: doubao/wenxin/qianwen/yuanbao/xinghuo"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get raw probe responses for a task (full Q&A pairs)."""
    service = MultiModelProbeService(db, current_user.customer_id)
    responses = await service.get_raw_responses(task_id, model_name, limit)

    return {
        "total": len(responses),
        "responses": [
            {
                "id": str(r.id),
                "model_name": r.model_name,
                "model_cn": r.model_cn,
                "keyword": r.keyword,
                "keyword_type": r.keyword_type,
                "question_round": r.question_round,
                "question_text": r.question_text,
                "response_text": r.response_text,
                "response_length": r.response_length,
                "api_latency_ms": r.api_latency_ms,
                "execution_status": r.execution_status,
                "is_fallback_response": r.is_fallback_response,
                "probed_at": r.probed_at.isoformat() if r.probed_at else None,
            }
            for r in responses
        ],
    }


@router.get("/responses/{response_id}")
async def get_single_response(
    response_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single raw response with its structured extraction."""
    from sqlalchemy import select
    from app.services.multi_model_probe.models import ModelProbeResponse, ProbeExtraction

    result = await db.execute(
        select(ModelProbeResponse).where(
            ModelProbeResponse.id == response_id,
            ModelProbeResponse.customer_id == current_user.customer_id,
        )
    )
    raw = result.scalar_one_or_none()
    if not raw:
        raise HTTPException(status_code=404, detail="Response not found")

    extraction = None
    if raw.extraction:
        ext = raw.extraction
        extraction = {
            "id": str(ext.id),
            "brand_mentioned": ext.brand_mentioned,
            "brand_name_found": ext.brand_name_found,
            "mention_count": ext.mention_count,
            "rank_position": ext.rank_position,
            "rank_in_category": ext.rank_in_category,
            "competitors_mentioned": ext.competitors_mentioned,
            "recommends_competitor": ext.recommends_competitor,
            "preferred_competitor": ext.preferred_competitor,
            "info_is_accurate": ext.info_is_accurate,
            "info_conflicts": ext.info_conflicts,
            "info_errors": ext.info_errors,
            "consistency_score": ext.consistency_score,
            "negative_detected": ext.negative_detected,
            "negative_content": ext.negative_content,
            "negative_category": ext.negative_category,
            "risk_level": ext.risk_level,
            "cited_sources": ext.cited_sources,
            "source_count": ext.source_count,
            "authoritative_source_count": ext.authoritative_source_count,
            "response_sentiment": ext.response_sentiment,
            "response_completeness": ext.response_completeness,
            "keyword_coverage": ext.keyword_coverage,
            "has_recommendation": ext.has_recommendation,
            "parsing_confidence": ext.parsing_confidence,
            "parser_model": ext.parser_model,
            "parser_version": ext.parser_version,
            "is_human_corrected": ext.is_human_corrected,
            "corrected_at": ext.corrected_at.isoformat() if ext.corrected_at else None,
            "correction_notes": ext.correction_notes,
        }

    return {
        "id": str(raw.id),
        "model_name": raw.model_name,
        "model_cn": raw.model_cn,
        "keyword": raw.keyword,
        "keyword_type": raw.keyword_type,
        "question_round": raw.question_round,
        "question_text": raw.question_text,
        "system_prompt": raw.system_prompt,
        "response_text": raw.response_text,
        "response_length": raw.response_length,
        "tokens_input": raw.tokens_input,
        "tokens_output": raw.tokens_output,
        "api_latency_ms": raw.api_latency_ms,
        "execution_status": raw.execution_status,
        "error_message": raw.error_message,
        "retry_count": raw.retry_count,
        "is_fallback_response": raw.is_fallback_response,
        "extraction": extraction,
    }


# ════════════════════════════════════════════════════════════════
# Extractions & Statistics
# ════════════════════════════════════════════════════════════════

@router.get("/tasks/{task_id}/extractions")
async def list_extractions(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all structured extraction results for a task."""
    service = MultiModelProbeService(db, current_user.customer_id)
    extractions = await service.get_extractions(task_id)

    return {
        "total": len(extractions),
        "extractions": [
            {
                "id": str(e.id),
                "response_id": str(e.response_id),
                "model_name": e.response.model_name if e.response else None,
                "brand_mentioned": e.brand_mentioned,
                "rank_position": e.rank_position,
                "competitors_mentioned": e.competitors_mentioned,
                "recommends_competitor": e.recommends_competitor,
                "info_is_accurate": e.info_is_accurate,
                "negative_detected": e.negative_detected,
                "risk_level": e.risk_level,
                "response_sentiment": e.response_sentiment,
                "parsing_confidence": e.parsing_confidence,
                "is_human_corrected": e.is_human_corrected,
            }
            for e in extractions
        ],
    }


@router.get("/tasks/{task_id}/statistics")
async def get_probe_statistics(
    task_id: uuid.UUID,
    model_name: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get aggregate statistics for a probe task.

    Returns overall stats + per-model breakdown.
    Includes: brand mention rate, avg rank, competitor preference rate,
    accuracy rate, negative content count, exposure level scoring.
    """
    service = MultiModelProbeService(db, current_user.customer_id)
    stats = await service.get_statistics(task_id, model_name)

    return {
        "task_id": str(task_id),
        "statistics": [
            {
                "id": str(s.id),
                "model_name": s.model_name,
                "total_probes": s.total_probes,
                "brand_mention_rate": s.brand_mention_rate,
                "avg_rank_position": s.avg_rank_position,
                "competitor_preference_rate": s.competitor_preference_rate,
                "top_competitors": s.top_competitors,
                "info_error_count": s.info_error_count,
                "negative_content_count": s.negative_content_count,
                "accuracy_rate": s.accuracy_rate,
                "exposure_level": s.exposure_level,
                "exposure_score": s.exposure_score,
                "total_cited_sources": s.total_cited_sources,
                "authoritative_sources": s.authoritative_sources,
                "positive_count": s.positive_count,
                "neutral_count": s.neutral_count,
                "negative_count": s.negative_count,
            }
            for s in stats
        ],
    }


# ════════════════════════════════════════════════════════════════
# Human correction
# ════════════════════════════════════════════════════════════════

@router.patch("/extractions/{extraction_id}/correct")
async def correct_extraction(
    extraction_id: uuid.UUID,
    corrections: dict,
    notes: str = "",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Apply human correction to an AI-generated extraction.

    Body: {"corrections": {"rank_position": 3, "brand_mentioned": true, ...}, "notes": "..."}
    Corrected fields are tracked with old/new values for audit trail.
    """
    service = MultiModelProbeService(db, current_user.customer_id)
    ext = await service.correct_extraction(
        extraction_id, current_user.id,
        corrections.get("corrections", corrections),
        corrections.get("notes", notes) if isinstance(corrections, dict) else notes,
    )

    return {
        "id": str(ext.id),
        "is_human_corrected": ext.is_human_corrected,
        "corrected_fields": ext.corrected_fields,
        "corrected_at": ext.corrected_at.isoformat() if ext.corrected_at else None,
        "correction_notes": ext.correction_notes,
    }


# ════════════════════════════════════════════════════════════════
# Export
# ════════════════════════════════════════════════════════════════

@router.get("/tasks/{task_id}/export")
async def export_probe_report(
    task_id: uuid.UUID,
    format: str = Query("json", description="Export format: json or csv"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export the complete probe report for a task.

    JSON format: Full structured data with raw responses, extractions, statistics.
    CSV format: Flattened tabular data for Excel import.
    """
    service = MultiModelProbeService(db, current_user.customer_id)

    execution = await service.get_execution(task_id)
    raw_responses = await service.get_raw_responses(task_id, limit=500)
    extractions = await service.get_extractions(task_id)
    stats = await service.get_statistics(task_id)

    if format == "csv":
        # Flatten to CSV-friendly rows
        import io, csv as csv_module
        output = io.StringIO()
        writer = csv_module.writer(output)
        writer.writerow([
            "模型", "关键词", "类型", "轮次", "提问", "回答(前200字)",
            "品牌提及", "排名", "推荐竞品", "信息准确", "负面内容", "情感",
            "响应时间ms", "状态"
        ])
        for r in raw_responses:
            ext = r.extraction
            writer.writerow([
                r.model_cn, r.keyword, r.keyword_type, r.question_round,
                r.question_text[:100], r.response_text[:200],
                "是" if (ext and ext.brand_mentioned) else "否",
                ext.rank_position if ext else "",
                "是" if (ext and ext.recommends_competitor) else "否",
                "是" if (ext and ext.info_is_accurate) else "否",
                ext.negative_content[:100] if (ext and ext.negative_content) else "",
                ext.response_sentiment if ext else "",
                r.api_latency_ms or "", r.execution_status,
            ])
        return {"format": "csv", "data": output.getvalue()}

    return {
        "task_id": str(task_id),
        "execution": {
            "status": execution.status if execution else "unknown",
            "total_questions": execution.total_questions if execution else 0,
            "total_duration_ms": execution.total_duration_ms if execution else 0,
        },
        "statistics": [
            {
                "model_name": s.model_name,
                "brand_mention_rate": s.brand_mention_rate,
                "avg_rank_position": s.avg_rank_position,
                "exposure_level": s.exposure_level,
            }
            for s in stats
        ],
        "raw_responses_count": len(raw_responses),
        "extractions_count": len(extractions),
    }

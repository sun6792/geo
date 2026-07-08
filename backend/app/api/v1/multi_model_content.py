"""P6: Agent 3 Multi-Model Content API — gap-driven generation + derivatives + model variants."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.services.multi_model_content import EnhancedGenerationService

router = APIRouter(prefix="/content/multi-model", tags=["Multi-Model Content"])


# ════════════════════════════════════════════════════════════════
# Main: Generate from gaps
# ════════════════════════════════════════════════════════════════

@router.post("/generate-from-gaps")
async def generate_content_from_gaps(
    gap_ids: list[uuid.UUID],
    generate_derivations: bool = True,
    generate_model_variants: bool = True,
    generate_ancillary: bool = False,
    target_models: list[str] | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Execute complete Agent 3 pipeline from diagnosis gaps.

    Flow: gaps → master article → 3 derivations + 5 model variants + ancillary → auto-review

    Body: {"gap_ids": ["uuid1", "uuid2"], "generate_derivations": true,
           "generate_model_variants": true, "target_models": ["doubao","wenxin"]}
    """
    service = EnhancedGenerationService(db, current_user["customer_id"])
    result = await service.generate_from_gaps(
        gap_ids=gap_ids,
        created_by=current_user["user_id"],
        generate_derivations=generate_derivations,
        generate_model_variants=generate_model_variants,
        generate_ancillary=generate_ancillary,
        target_models=target_models,
    )
    return result


# ════════════════════════════════════════════════════════════════
# View derivatives for a draft
# ════════════════════════════════════════════════════════════════

@router.get("/drafts/{draft_id}/derivatives")
async def list_derivatives(
    draft_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get all content derivatives for a master draft.

    Returns three-in-one versions + five-model variants + ancillary content.
    Each derivative has: type, title, body, word_count, creation time.
    """
    service = EnhancedGenerationService(db, current_user["customer_id"])
    derivatives = await service.get_derivatives(draft_id)

    return {
        "draft_id": str(draft_id),
        "total": len(derivatives),
        "derivations": [
            d for d in derivatives if d.derivative_type in ("seo", "ai_qa", "short_video")
        ],
        "model_variants": [
            d for d in derivatives if d.derivative_type in ("doubao", "wenxin", "qianwen", "yuanbao", "xinghuo")
        ],
        "ancillary": [
            d for d in derivatives if d.derivative_type in ("photo_captions", "qa_replies", "clarification")
        ],
        "items": [
            {
                "id": str(d.id),
                "type": d.derivative_type,
                "target_model": d.target_model,
                "title": d.title,
                "word_count": d.word_count,
                "tokens_used": d.tokens_used,
                "generation_time_ms": d.generation_time_ms,
                "status": d.status,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in derivatives
        ],
    }


@router.get("/drafts/{draft_id}/model-variants")
async def get_model_variants(
    draft_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get per-model content variants for comparison view.

    Returns content for each model (doubao/wenxin/qianwen/yuanbao/xinghuo).
    """
    service = EnhancedGenerationService(db, current_user["customer_id"])
    variants = await service.get_model_variants(draft_id)

    result = {}
    for model_key in ("doubao", "wenxin", "qianwen", "yuanbao", "xinghuo"):
        v = variants.get(model_key)
        if v:
            result[model_key] = {
                "id": str(v.id),
                "title": v.title,
                "body_markdown": v.body_markdown,
                "word_count": v.word_count,
                "tokens_used": v.tokens_used,
                "generation_time_ms": v.generation_time_ms,
            }
        else:
            result[model_key] = None

    return {"draft_id": str(draft_id), "variants": result}


# ════════════════════════════════════════════════════════════════
# Single model regeneration
# ════════════════════════════════════════════════════════════════

@router.post("/drafts/{draft_id}/regenerate-model")
async def regenerate_model_variant(
    draft_id: uuid.UUID,
    model_key: str = Query(..., description="doubao/wenxin/qianwen/yuanbao/xinghuo"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Regenerate a specific model variant for a master draft."""
    from sqlalchemy import select
    from app.models.content import ContentDraft

    result = await db.execute(
        select(ContentDraft).where(
            ContentDraft.id == draft_id,
            ContentDraft.customer_id == current_user["customer_id"],
        )
    )
    draft = result.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    from app.services.multi_model_content.prompt_templates import format_model_rewrite_prompt
    prompt = format_model_rewrite_prompt(model_key, draft.body_markdown)

    import httpx
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {draft.customer_id}", "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "temperature": 0.7, "max_tokens": 3000,
                  "messages": [{"role": "user", "content": prompt}]},
        )
        content = resp.json()["choices"][0]["message"]["content"] if resp.status_code == 200 else "[生成失败]"

    return {"model_key": model_key, "content": content, "word_count": len(content)}


# ════════════════════════════════════════════════════════════════
# Content status
# ════════════════════════════════════════════════════════════════

@router.get("/stats")
async def get_content_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get content generation statistics for the current customer."""
    from sqlalchemy import func, select
    from app.models.content import ContentDraft
    from app.models.identity import ContentDerivative

    drafts_count = (await db.execute(
        select(func.count(ContentDraft.id)).where(
            ContentDraft.customer_id == current_user["customer_id"],
        )
    )).scalar() or 0

    derivatives_count = (await db.execute(
        select(func.count(ContentDerivative.id)).where(
            ContentDerivative.customer_id == current_user["customer_id"],
        )
    )).scalar() or 0

    # Count by type
    type_counts = {}
    result = await db.execute(
        select(ContentDerivative.derivative_type, func.count(ContentDerivative.id))
        .where(ContentDerivative.customer_id == current_user["customer_id"])
        .group_by(ContentDerivative.derivative_type)
    )
    for row in result.all():
        type_counts[row[0]] = row[1]

    return {
        "total_drafts": drafts_count,
        "total_derivatives": derivatives_count,
        "by_type": type_counts,
    }

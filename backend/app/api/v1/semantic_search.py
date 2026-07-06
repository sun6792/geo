"""P2 Semantic Search & Embedding API — Chroma-powered knowledge base search."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.services.embedding_service import EmbeddingService

router = APIRouter(tags=["P2: Semantic Search"])


@router.get("/search")
async def semantic_search(
    q: str = Query(..., description="Natural language query"), top_k: int = Query(10, ge=1, le=50),
    threshold: float = Query(0.3, ge=0, le=1),
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    """Semantic search across the knowledge base using Chroma vector store."""
    svc = EmbeddingService(db, current_user["customer_id"])
    return await svc.semantic_search(q, top_k, threshold)


@router.get("/content-sources")
async def get_content_sources(
    q: str = Query(...), top_k: int = Query(5, ge=1, le=20),
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    """Get relevant KB sources for content generation."""
    svc = EmbeddingService(db, current_user["customer_id"])
    return await svc.get_content_sources(q, top_k)


@router.post("/assets/{asset_id}/embed")
async def embed_asset(asset_id: uuid.UUID,
    current_user: dict = Depends(require_permission("kb", "update")), db: AsyncSession = Depends(get_db)):
    """Generate and store vector embeddings for a knowledge base asset."""
    svc = EmbeddingService(db, current_user["customer_id"])
    chroma_ids = await svc.embed_asset(asset_id)
    return {"embedded": len(chroma_ids), "chroma_ids": chroma_ids}


@router.post("/reindex")
async def reindex_all(
    current_user: dict = Depends(require_permission("kb", "update")), db: AsyncSession = Depends(get_db)):
    """Re-index all published assets for the current customer."""
    svc = EmbeddingService(db, current_user["customer_id"])
    return await svc.reindex_all()


@router.get("/index-stats")
async def get_index_stats(
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get vector index statistics."""
    svc = EmbeddingService(db, current_user["customer_id"])
    return await svc.get_index_stats()

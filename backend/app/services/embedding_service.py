"""Embedding service — bridges knowledge base assets with Chroma vector store.

Handles: automatic embedding on asset create/update, semantic search,
content sourcing for generation, batch re-indexing.
"""

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.integrations.vector_store.chroma_store import chroma_store, chunk_text
from app.models.knowledge_base import KbAsset, KbEmbedding


class EmbeddingService:
    """Manages vector embeddings for knowledge base assets."""

    def __init__(self, db: AsyncSession, customer_id: uuid.UUID):
        self.db = db
        self.customer_id = customer_id

    async def embed_asset(self, asset_id: uuid.UUID) -> list[str]:
        """Generate and store embeddings for a knowledge base asset.

        1. Extract text from the asset (content_text or content_json)
        2. Chunk the text
        3. Store chunks in Chroma
        4. Record embedding metadata in PostgreSQL
        """
        result = await self.db.execute(
            select(KbAsset).where(KbAsset.id == asset_id, KbAsset.customer_id == self.customer_id)
        )
        asset = result.scalar_one_or_none()
        if not asset:
            raise NotFoundException("KbAsset", str(asset_id))

        # Build text to embed
        text_to_embed = asset.content_text or ""
        if asset.content_json:
            import json
            # Flatten JSON content into searchable text
            for key, value in asset.content_json.items():
                if isinstance(value, str):
                    text_to_embed += f"\n{key}: {value}"
                elif isinstance(value, list):
                    text_to_embed += f"\n{key}: " + ", ".join(str(v) for v in value)

        # Remove old embeddings for this asset version first (always, even if empty)
        existing = (await self.db.execute(
            select(KbEmbedding).where(
                KbEmbedding.asset_id == asset_id,
                KbEmbedding.asset_version == asset.version,
            )
        )).scalars().all()
        existing_count = len(existing)
        for emb in existing:
            await self.db.delete(emb)
        await chroma_store.delete_asset_chunks(self.customer_id, asset_id, asset.version, existing_count)

        if not text_to_embed.strip():
            return []

        # Chunk the text
        chunks = chunk_text(text_to_embed)

        # Add new embeddings to Chroma
        chroma_ids = await chroma_store.add_asset_chunks(
            self.customer_id, asset_id, asset.version, chunks,
        )

        # Record embedding metadata in PostgreSQL
        embedding_model = "text-embedding-3-small"
        for i, (chunk_text_content, chroma_id) in enumerate(zip(chunks, chroma_ids)):
            self.db.add(KbEmbedding(
                customer_id=self.customer_id,
                asset_id=asset_id,
                asset_version=asset.version,
                chroma_collection=chroma_store._collection_name(self.customer_id),
                chroma_id=chroma_id,
                chunk_index=i,
                chunk_text=chunk_text_content,
                embedding_model=embedding_model,
                token_count=len(chunk_text_content.split()),
            ))

        await self.db.flush()
        return chroma_ids

    async def semantic_search(self, query: str, top_k: int = 10, threshold: float = 0.3) -> list[dict]:
        """Semantic search across the customer's knowledge base.

        Returns enriched results with asset metadata from PostgreSQL.
        """
        results = await chroma_store.search(self.customer_id, query, top_k, threshold)

        # Enrich with asset metadata
        asset_ids = set()
        for r in results:
            if r.get("asset_id"):
                try:
                    asset_ids.add(uuid.UUID(r["asset_id"]))
                except (ValueError, TypeError):
                    pass

        # Batch load asset metadata
        asset_map = {}
        if asset_ids:
            assets_result = await self.db.execute(
                select(KbAsset).where(
                    KbAsset.id.in_(list(asset_ids)),
                    KbAsset.customer_id == self.customer_id,
                )
            )
            for a in assets_result.scalars().all():
                asset_map[str(a.id)] = {"title": a.title, "asset_type": a.asset_type, "slug": a.slug, "tags": a.tags}

        # Enrich results
        for r in results:
            r["asset_meta"] = asset_map.get(r.get("asset_id", ""), {})

        return results

    async def get_content_sources(self, query: str, top_k: int = 5) -> list[dict]:
        """Get knowledge base sources for content generation.

        Returns the most relevant KB assets and their content for use as
        source material in AI content generation.
        """
        results = await self.semantic_search(query, top_k, threshold=0.2)

        # Group by asset and collect unique assets
        asset_ids = set()
        for r in results:
            if r.get("asset_id"):
                try:
                    asset_ids.add(uuid.UUID(r["asset_id"]))
                except (ValueError, TypeError):
                    pass

        # Load full asset content
        sources = []
        if asset_ids:
            assets_result = await self.db.execute(
                select(KbAsset).where(
                    KbAsset.id.in_(list(asset_ids)),
                    KbAsset.customer_id == self.customer_id,
                    KbAsset.is_latest == True,
                )
            )
            for a in assets_result.scalars().all():
                sources.append({
                    "asset_id": str(a.id),
                    "title": a.title,
                    "asset_type": a.asset_type,
                    "content_text": a.content_text,
                    "content_json": a.content_json,
                    "tags": a.tags,
                })

        return sources

    async def reindex_all(self) -> dict:
        """Re-index all published assets for the current customer."""
        result = await self.db.execute(
            select(KbAsset).where(
                KbAsset.customer_id == self.customer_id,
                KbAsset.is_latest == True,
                KbAsset.status == "published",
            )
        )
        assets = result.scalars().all()

        stats = {"total": len(assets), "embedded": 0, "skipped": 0, "failed": 0}
        for asset in assets:
            try:
                ids = await self.embed_asset(asset.id)
                if ids:
                    stats["embedded"] += 1
                else:
                    stats["skipped"] += 1
            except Exception:
                stats["failed"] += 1

        return stats

    async def get_index_stats(self) -> dict:
        """Get vector index statistics for the customer."""
        result = await self.db.execute(
            select(KbEmbedding).where(KbEmbedding.customer_id == self.customer_id)
        )
        embeddings = result.scalars().all()

        asset_ids = set(str(e.asset_id) for e in embeddings)
        total_chunks = len(embeddings)

        # Count published assets
        from sqlalchemy import func
        published = (await self.db.execute(
            select(func.count(KbAsset.id)).where(
                KbAsset.customer_id == self.customer_id,
                KbAsset.is_latest == True,
                KbAsset.status == "published",
            )
        )).scalar() or 0

        return {
            "total_chunks": total_chunks,
            "indexed_assets": len(asset_ids),
            "total_published_assets": published,
            "index_coverage": round(len(asset_ids) / max(published, 1) * 100, 1),
            "embedding_model": "text-embedding-3-small",
        }

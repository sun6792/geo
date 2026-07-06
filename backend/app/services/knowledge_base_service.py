"""Knowledge Base service with versioning, categories, and asset management."""

import uuid
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.core.pagination import PaginationParams
from app.models.knowledge_base import KbAsset, KbCategory, KbChangelog, KbAssetRelationship


class KnowledgeBaseService:
    """Knowledge base CRUD with version tracking and category management."""

    def __init__(self, db: AsyncSession, customer_id: uuid.UUID):
        self.db = db
        self.customer_id = customer_id

    # ── Categories ────────────────────────────────────────────

    async def list_categories(self) -> list[KbCategory]:
        result = await self.db.execute(
            select(KbCategory)
            .where(KbCategory.customer_id == self.customer_id)
            .order_by(KbCategory.sort_order)
        )
        return list(result.scalars().all())

    async def create_category(self, name: str, slug: str, parent_id: Optional[uuid.UUID] = None,
                               description: Optional[str] = None, created_by: Optional[uuid.UUID] = None) -> KbCategory:
        cat = KbCategory(
            customer_id=self.customer_id, name=name, slug=slug,
            parent_id=parent_id, description=description, created_by=created_by
        )
        self.db.add(cat)
        await self.db.flush()
        return cat

    async def update_category(self, category_id: uuid.UUID, **kwargs) -> KbCategory:
        cat = await self._get_category(category_id)
        for k, v in kwargs.items():
            if v is not None and hasattr(cat, k):
                setattr(cat, k, v)
        await self.db.flush()
        return cat

    async def delete_category(self, category_id: uuid.UUID) -> None:
        cat = await self._get_category(category_id)
        await self.db.delete(cat)
        await self.db.flush()

    async def _get_category(self, category_id: uuid.UUID) -> KbCategory:
        result = await self.db.execute(
            select(KbCategory).where(KbCategory.id == category_id, KbCategory.customer_id == self.customer_id)
        )
        cat = result.scalar_one_or_none()
        if not cat:
            raise NotFoundException("Category", str(category_id))
        return cat

    # ── Assets ────────────────────────────────────────────────

    async def list_assets(self, pagination: PaginationParams, asset_type: Optional[str] = None,
                          status: Optional[str] = None, category_id: Optional[uuid.UUID] = None,
                          search: Optional[str] = None) -> tuple[list[KbAsset], int]:
        query = select(KbAsset).where(KbAsset.customer_id == self.customer_id, KbAsset.is_latest == True)
        count_q = select(func.count(KbAsset.id)).where(KbAsset.customer_id == self.customer_id, KbAsset.is_latest == True)

        if asset_type:
            query = query.where(KbAsset.asset_type == asset_type)
            count_q = count_q.where(KbAsset.asset_type == asset_type)
        if status:
            query = query.where(KbAsset.status == status)
            count_q = count_q.where(KbAsset.status == status)
        if category_id:
            query = query.where(KbAsset.category_id == category_id)
            count_q = count_q.where(KbAsset.category_id == category_id)
        if search:
            query = query.where(KbAsset.title.ilike(f"%{search}%") | KbAsset.content_text.ilike(f"%{search}%"))
            count_q = count_q.where(KbAsset.title.ilike(f"%{search}%") | KbAsset.content_text.ilike(f"%{search}%"))

        total = (await self.db.execute(count_q)).scalar() or 0
        assets = (await self.db.execute(
            query.order_by(KbAsset.updated_at.desc()).offset(pagination.offset).limit(pagination.limit)
        )).scalars().all()
        return list(assets), total

    async def create_asset(self, data: dict) -> KbAsset:
        """Create a new knowledge asset (version 1)."""
        # Exclude 'metadata' — it collides with SQLAlchemy's Base.metadata
        safe_data = {k: v for k, v in data.items() if hasattr(KbAsset, k) and k != "metadata"}
        # Map 'metadata' → 'extra_meta' (column was renamed due to SQLAlchemy conflict)
        if data.get("metadata"):
            safe_data["extra_meta"] = data["metadata"]
        asset = KbAsset(
            customer_id=self.customer_id,
            **safe_data
        )
        self.db.add(asset)
        await self.db.flush()

        # Log changelog
        self.db.add(KbChangelog(
            customer_id=self.customer_id, asset_id=asset.id,
            change_type="created", changed_by=data.get("created_by"),
            changes_json={"title": asset.title, "asset_type": asset.asset_type}
        ))
        await self.db.flush()
        return asset

    async def update_asset(self, asset_id: uuid.UUID, data: dict) -> KbAsset:
        """Update an asset — creates a new version, marks old version as not latest."""
        old = await self._get_asset(asset_id)

        # Handle metadata → extra_meta mapping
        if "metadata" in data:
            data["extra_meta"] = data.pop("metadata")

        # Mark old version as not latest
        await self.db.execute(
            update(KbAsset).where(KbAsset.id == asset_id).values(is_latest=False)
        )

        # Create new version
        new_version = old.version + 1
        new_asset = KbAsset(
            customer_id=self.customer_id,
            category_id=old.category_id,
            title=data.get("title", old.title),
            slug=old.slug,
            asset_type=old.asset_type,
            content_type=data.get("content_type", old.content_type),
            content_text=data.get("content_text", old.content_text),
            content_json=data.get("content_json", old.content_json),
            file_path=data.get("file_path", old.file_path),
            status=data.get("status", old.status),
            version=new_version,
            is_latest=True,
            tags=data.get("tags", old.tags),
            extra_meta=data.get("extra_meta", old.extra_meta),
            created_by=data.get("updated_by", old.created_by),
        )
        self.db.add(new_asset)
        await self.db.flush()

        # Log changelog
        self.db.add(KbChangelog(
            customer_id=self.customer_id, asset_id=new_asset.id,
            change_type="updated", changed_by=data.get("updated_by"),
            changes_json={"version": new_version, "changed_fields": list(data.keys())}
        ))
        await self.db.flush()
        return new_asset

    async def get_asset(self, asset_id: uuid.UUID) -> KbAsset:
        return await self._get_asset(asset_id)

    async def get_asset_versions(self, slug: str) -> list[KbAsset]:
        result = await self.db.execute(
            select(KbAsset)
            .where(KbAsset.customer_id == self.customer_id, KbAsset.slug == slug)
            .order_by(KbAsset.version.desc())
        )
        return list(result.scalars().all())

    async def archive_asset(self, asset_id: uuid.UUID) -> None:
        asset = await self._get_asset(asset_id)
        asset.status = "archived"
        await self.db.flush()

    async def _get_asset(self, asset_id: uuid.UUID) -> KbAsset:
        result = await self.db.execute(
            select(KbAsset).where(KbAsset.id == asset_id, KbAsset.customer_id == self.customer_id)
        )
        asset = result.scalar_one_or_none()
        if not asset:
            raise NotFoundException("Asset", str(asset_id))
        return asset

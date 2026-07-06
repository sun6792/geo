"""P3 Industry Template Service — One-click customer initialization from templates."""

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.models.template import IndustryTemplate
from app.models.knowledge_base import KbCategory, KbAsset
from app.models.agent import DetectionTask, Competitor


class TemplateService:
    """Industry template management and one-click customer initialization."""

    def __init__(self, db: AsyncSession, customer_id: uuid.UUID | None = None):
        self.db = db
        self.customer_id = customer_id

    # ── Template CRUD ─────────────────────────────────────────

    async def list_templates(self, industry: Optional[str] = None) -> list[IndustryTemplate]:
        query = select(IndustryTemplate).where(IndustryTemplate.is_active == True)
        if industry:
            query = query.where(IndustryTemplate.industry == industry)
        query = query.where(
            (IndustryTemplate.customer_id == self.customer_id) | (IndustryTemplate.customer_id.is_(None))
        ).order_by(IndustryTemplate.industry, IndustryTemplate.name)
        return list((await self.db.execute(query)).scalars().all())

    async def get_template(self, template_id: uuid.UUID) -> IndustryTemplate:
        result = await self.db.execute(select(IndustryTemplate).where(IndustryTemplate.id == template_id))
        t = result.scalar_one_or_none()
        if not t:
            raise NotFoundException("IndustryTemplate", str(template_id))
        return t

    async def create_template(self, data: dict) -> IndustryTemplate:
        data["customer_id"] = self.customer_id
        data["is_system"] = False
        tmpl = IndustryTemplate(**data)
        self.db.add(tmpl)
        await self.db.flush()
        return tmpl

    async def delete_template(self, template_id: uuid.UUID) -> None:
        t = await self.get_template(template_id)
        if t.is_system:
            raise ValidationException("System templates cannot be deleted")
        await self.db.delete(t)
        await self.db.flush()

    # ── One-Click Initialization ──────────────────────────────

    async def initialize_from_template(self, template_id: uuid.UUID, created_by: uuid.UUID) -> dict:
        """Initialize a customer's account from an industry template.

        Creates: KB categories + assets, detection keywords, competitors, channels.
        Returns a summary of what was created.
        """
        if not self.customer_id:
            raise ValidationException("customer_id is required for initialization")

        template = await self.get_template(template_id)
        stats = {"categories": 0, "assets": 0, "keywords": 0, "competitors": 0}

        # 1. Create KB asset structure
        for asset_def in template.asset_structure:
            # Create category if specified
            cat_name = asset_def.get("category")
            cat_id = None
            if cat_name:
                cat = KbCategory(
                    customer_id=self.customer_id, name=cat_name,
                    slug=cat_name.lower().replace(" ", "-")[:200],
                    created_by=created_by,
                )
                self.db.add(cat)
                await self.db.flush()
                cat_id = cat.id
                stats["categories"] += 1

            # Create asset
            asset = KbAsset(
                customer_id=self.customer_id, category_id=cat_id,
                title=asset_def.get("name", "New Asset"),
                slug=asset_def.get("name", "new-asset").lower().replace(" ", "-")[:200],
                asset_type=asset_def.get("asset_type", "basic"),
                content_type="text",
                content_text=asset_def.get("description", ""),
                status="published",
                tags=asset_def.get("tags", []),
                created_by=created_by,
            )
            self.db.add(asset)
            stats["assets"] += 1

        # 2. Create detection task with preset keywords
        if template.preset_keywords:
            task = DetectionTask(
                customer_id=self.customer_id,
                name=f"{template.name} — 自动探测任务",
                keywords=template.preset_keywords,
                target_models=["doubao", "wenxin", "qianwen", "yuanbao", "xinghuo", "deepseek", "kimi"],
                schedule_type="weekly",
                is_active=True,
                created_by=created_by,
            )
            self.db.add(task)
            stats["keywords"] = len(template.preset_keywords)

        # 3. Create competitor configs
        for comp in template.competitor_suggestions:
            self.db.add(Competitor(
                customer_id=self.customer_id,
                name=comp.get("name", ""),
                industry=template.industry,
                tags=comp.get("tags", []),
                created_by=created_by,
            ))
            stats["competitors"] += 1

        await self.db.flush()
        return stats

    async def get_industries(self) -> list[str]:
        """List all available industries."""
        result = await self.db.execute(
            select(IndustryTemplate.industry).where(IndustryTemplate.is_active == True).distinct()
        )
        return [r[0] for r in result.all()]

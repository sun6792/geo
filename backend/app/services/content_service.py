"""Content creation service — briefs, drafts, templates, and AI generation."""

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, KbSourceRequiredException
from app.core.pagination import PaginationParams
from app.models.content import ContentBrief, ContentDraft, ContentGenerationRun, ContentTemplate


class ContentService:
    """Content brief, draft, and template management."""

    def __init__(self, db: AsyncSession, customer_id: uuid.UUID):
        self.db = db
        self.customer_id = customer_id

    # ── Briefs ────────────────────────────────────────────────

    async def list_briefs(self, pagination: PaginationParams, status: Optional[str] = None) -> tuple[list[ContentBrief], int]:
        query = select(ContentBrief).where(ContentBrief.customer_id == self.customer_id)
        count_q = select(func.count(ContentBrief.id)).where(ContentBrief.customer_id == self.customer_id)
        if status:
            query = query.where(ContentBrief.status == status)
            count_q = count_q.where(ContentBrief.status == status)

        total = (await self.db.execute(count_q)).scalar() or 0
        briefs = (await self.db.execute(
            query.order_by(ContentBrief.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
        )).scalars().all()
        return list(briefs), total

    async def create_brief(self, data: dict) -> ContentBrief:
        """Create a content brief. Must include source_kb_asset_ids."""
        if not data.get("source_kb_asset_ids"):
            raise KbSourceRequiredException()

        brief = ContentBrief(customer_id=self.customer_id, **data)
        self.db.add(brief)
        await self.db.flush()
        return brief

    async def get_brief(self, brief_id: uuid.UUID) -> ContentBrief:
        result = await self.db.execute(
            select(ContentBrief).where(ContentBrief.id == brief_id, ContentBrief.customer_id == self.customer_id)
        )
        brief = result.scalar_one_or_none()
        if not brief:
            raise NotFoundException("ContentBrief", str(brief_id))
        return brief

    async def update_brief(self, brief_id: uuid.UUID, data: dict) -> ContentBrief:
        brief = await self.get_brief(brief_id)
        for k, v in data.items():
            if v is not None and hasattr(brief, k):
                setattr(brief, k, v)
        await self.db.flush()
        return brief

    # ── Drafts ─────────────────────────────────────────────────

    async def list_drafts(self, brief_id: uuid.UUID) -> list[ContentDraft]:
        result = await self.db.execute(
            select(ContentDraft)
            .where(ContentDraft.brief_id == brief_id, ContentDraft.customer_id == self.customer_id)
            .order_by(ContentDraft.version.desc())
        )
        return list(result.scalars().all())

    async def get_draft(self, draft_id: uuid.UUID) -> ContentDraft:
        result = await self.db.execute(
            select(ContentDraft).where(ContentDraft.id == draft_id, ContentDraft.customer_id == self.customer_id)
        )
        draft = result.scalar_one_or_none()
        if not draft:
            raise NotFoundException("ContentDraft", str(draft_id))
        return draft

    async def update_draft(self, draft_id: uuid.UUID, data: dict) -> ContentDraft:
        draft = await self.get_draft(draft_id)
        for k, v in data.items():
            if v is not None and hasattr(draft, k):
                setattr(draft, k, v)
        await self.db.flush()
        return draft

    # ── Templates ─────────────────────────────────────────────

    async def list_templates(self) -> list[ContentTemplate]:
        result = await self.db.execute(
            select(ContentTemplate).where(
                (ContentTemplate.customer_id == self.customer_id) | (ContentTemplate.customer_id.is_(None)),
                ContentTemplate.is_active == True,
            ).order_by(ContentTemplate.content_type)
        )
        return list(result.scalars().all())

    async def create_template(self, data: dict) -> ContentTemplate:
        tmpl = ContentTemplate(customer_id=self.customer_id, **data)
        self.db.add(tmpl)
        await self.db.flush()
        return tmpl

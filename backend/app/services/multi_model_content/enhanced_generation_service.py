"""P6: Enhanced Generation Service — Agent 3 full orchestration.

Integrates:
- Master article generation from diagnosis gaps + KB assets
- Three-in-one content derivation (SEO / AI-QA / Short Video)
- Five-model differentiated rewriting (豆包/文心/千问/元宝/星火)
- Ancillary content (photo captions / Q&A replies / clarifications)
- Content quality validation
- Auto-submit to Agent 4 review queue
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.content import (
    ContentBrief, ContentDraft, ContentGenerationRun, ContentGenerationHistory,
)
from app.models.customer import Customer
from app.models.identity import ContentDerivative
from app.core.exceptions import NotFoundException, ValidationException

from app.services.multi_model_content.prompt_templates import (
    TEMPLATES, format_master_prompt, format_derivation_prompt,
    format_model_rewrite_prompt,
)
from app.services.multi_model_content.content_validator import (
    ContentValidator, ValidationResult,
)


class EnhancedGenerationService:
    """Agent 3: Complete content generation pipeline."""

    def __init__(self, db: AsyncSession, customer_id: uuid.UUID):
        self.db = db
        self.customer_id = customer_id
        self.api_key = settings.OPENAI_API_KEY or ""
        self.api_base = "https://api.deepseek.com/v1"
        self.validator = ContentValidator()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=180)
        return self._client

    # ════════════════════════════════════════════════════════════
    # Main: Full generation pipeline from Agent 2 gaps
    # ════════════════════════════════════════════════════════════

    async def generate_from_gaps(self,
                                   gap_ids: list[uuid.UUID],
                                   created_by: uuid.UUID,
                                   generate_derivations: bool = True,
                                   generate_model_variants: bool = True,
                                   generate_ancillary: bool = False,
                                   target_models: list[str] | None = None,
                                   ) -> dict:
        """Execute the complete Agent 3 pipeline from diagnosis gaps.

        1. Load gaps + KB assets + customer info
        2. Generate master article
        3. Derive three-in-one variants (SEO/AI-QA/ShortVideo)
        4. Rewrite for five models (豆包/文心/千问/元宝/星火)
        5. Generate ancillary content (optional)
        6. Validate all content
        7. Auto-submit master draft to Agent 4 review queue
        """
        from app.services.layered_diagnosis.models import DiagnosisGap
        from app.models.knowledge_base import KbAsset

        # ── 1. Load data ───────────────────────────────────────
        customer = await self._get_customer()
        company_name = customer.company_name or customer.name
        industry = customer.industry or ""

        gaps = (await self.db.execute(
            select(DiagnosisGap).where(
                DiagnosisGap.id.in_(gap_ids),
                DiagnosisGap.customer_id == self.customer_id,
            )
        )).scalars().all()

        if not gaps:
            raise ValidationException("No valid gaps found")

        # Build gap context for prompt
        gap_context = "\n".join([
            f"- [{g.priority}] {g.gap_name}: {g.description} → 需创建{g.content_type_needed or 'SEO文章'}"
            for g in gaps
        ])

        # Collect keywords from gaps
        all_keywords = []
        for g in gaps:
            all_keywords.extend(g.target_keywords or [])
        all_keywords = list(set(all_keywords))[:10]
        if not all_keywords:
            all_keywords = [company_name, industry]

        # Load KB assets
        kb_assets = (await self.db.execute(
            select(KbAsset).where(
                KbAsset.customer_id == self.customer_id,
                KbAsset.is_latest == True,
                KbAsset.status == "published",
            )
        )).scalars().all()

        kb_context = self._build_kb_context(list(kb_assets)) if kb_assets else ""
        main_business = gaps[0].target_keywords[0] if gaps[0].target_keywords else industry

        # ── 2. Generate master article ─────────────────────────
        system_prompt = format_master_prompt(
            company_name=company_name,
            industry=industry,
            main_business=main_business,
            keywords=all_keywords,
            word_count=1000,
            gap_context=gap_context,
            kb_context=kb_context,
        )

        master_content = await self._call_llm(
            system_prompt, "请创作完整主稿(Markdown格式)。", max_tokens=3000
        )

        # Persist master as a ContentDraft
        master_draft = await self._persist_draft(
            title=f"[GEO优化] {company_name} - 主稿",
            content=master_content,
            content_type="master",
            created_by=created_by,
            keywords=all_keywords,
            kb_sources=kb_assets,
            gap_ids=gap_ids,
        )

        # Validate
        validation = self.validator.validate(master_content)

        result = {
            "master_draft_id": str(master_draft.id),
            "master_title": master_draft.title,
            "validation": {
                "is_valid": validation.is_valid,
                "warnings_count": len(validation.warnings),
                "quality_score": validation.quality_score,
            },
            "derivations": [],
            "model_variants": [],
            "ancillary": [],
        }

        derivation_tasks = []
        model_tasks = []
        ancillary_tasks = []

        # ── 3. Three-in-one derivations ─────────────────────────
        if generate_derivations:
            for version_key in ["seo", "ai_qa", "short_video"]:
                derivation_tasks.append(self._generate_derivative(
                    version_key, master_content, master_draft.id,
                    created_by, company_name, all_keywords
                ))

        # ── 4. Five-model rewrites ─────────────────────────────
        if generate_model_variants:
            models = target_models or list(TEMPLATES["model_rewrite"].keys())
            for model in models:
                if model in TEMPLATES["model_rewrite"]:
                    model_tasks.append(self._generate_model_variant(
                        model, master_content, master_draft.id,
                        created_by, company_name
                    ))

        # ── 5. Ancillary content ───────────────────────────────
        if generate_ancillary:
            ancillary_tasks.append(self._generate_photo_captions(
                company_name, industry, master_draft.id, created_by
            ))
            ancillary_tasks.append(self._generate_qa_replies(
                company_name, industry, all_keywords, master_draft.id, created_by
            ))

        # Execute all in parallel
        all_derivations = await asyncio.gather(*derivation_tasks, return_exceptions=True)
        all_variants = await asyncio.gather(*model_tasks, return_exceptions=True)
        all_ancillary = await asyncio.gather(*ancillary_tasks, return_exceptions=True)

        result["derivations"] = [d for d in all_derivations if isinstance(d, dict)]
        result["model_variants"] = [v for v in all_variants if isinstance(v, dict)]
        result["ancillary"] = [a for a in all_ancillary if isinstance(a, dict)]

        # ── 6. Auto-submit master to Agent 4 review ─────────────
        review = await self._auto_submit_for_review(master_draft.id, created_by)
        result["in_review"] = review is not None
        if review:
            result["review_id"] = str(review.id)

        result["summary"] = (
            f"Master + {len(result['derivations'])} derivations + "
            f"{len(result['model_variants'])} model variants + "
            f"{len(result['ancillary'])} ancillary. "
            f"{'Submitted for review.' if result['in_review'] else 'Review submission skipped.'}"
        )

        return result

    # ════════════════════════════════════════════════════════════
    # Individual generation methods
    # ════════════════════════════════════════════════════════════

    async def _generate_derivative(self, version_key: str, master_content: str,
                                     master_draft_id: uuid.UUID, created_by: uuid.UUID,
                                     company_name: str, keywords: list[str]) -> dict:
        """Generate a single three-in-one derivative."""
        t0 = time.time()
        template = TEMPLATES["derivation"].get(version_key, {})
        name_cn = {"seo": "百度SEO版", "ai_qa": "AI问答版", "short_video": "短视频脚本版"}[version_key]

        prompt = format_derivation_prompt(version_key, master_content,
                                           " ".join(keywords))

        content = await self._call_llm(
            system_prompt=f"你是专业内容创作助手。请将主稿改写为{name_cn}。只输出内容。",
            user_prompt=prompt,
            max_tokens=2500,
        )

        # Persist as ContentDerivative
        self.db.add(ContentDerivative(
            customer_id=self.customer_id,
            source_draft_id=master_draft_id,
            derivative_type=version_key,
            target_model=None,
            title=f"[{name_cn}] {company_name}",
            body_markdown=content,
            word_count=len(content),
            generation_prompt=prompt[:500],
            generation_model="deepseek-chat",
            tokens_used=len(content) // 2,
            generation_time_ms=(time.time() - t0) * 1000,
            status="draft",
            created_by=created_by,
        ))
        await self.db.flush()

        return {"type": version_key, "name": name_cn, "length": len(content),
                 "time_ms": int((time.time() - t0) * 1000)}

    async def _generate_model_variant(self, model_key: str, master_content: str,
                                        master_draft_id: uuid.UUID, created_by: uuid.UUID,
                                        company_name: str) -> dict:
        """Generate a single five-model differentiated rewrite."""
        t0 = time.time()
        template = TEMPLATES["model_rewrite"].get(model_key, {})
        name_cn = {"doubao": "豆包版", "wenxin": "文心版", "qianwen": "千问版",
                    "yuanbao": "元宝版", "xinghuo": "星火版"}[model_key]

        prompt = format_model_rewrite_prompt(model_key, master_content)

        content = await self._call_llm(
            system_prompt=f"你是{name_cn}内容创作者。请按照适配规范改写。只输出内容。",
            user_prompt=prompt,
            max_tokens=3000,
        )

        self.db.add(ContentDerivative(
            customer_id=self.customer_id,
            source_draft_id=master_draft_id,
            derivative_type=model_key,
            target_model=model_key,
            title=f"[{name_cn}] {company_name}",
            body_markdown=content,
            word_count=len(content),
            generation_prompt=prompt[:500],
            generation_model="deepseek-chat",
            tokens_used=len(content) // 2,
            generation_time_ms=(time.time() - t0) * 1000,
            status="draft",
            created_by=created_by,
        ))
        await self.db.flush()

        return {"model": model_key, "name": name_cn, "length": len(content),
                 "ecosystem": template.get("ecosystem", ""),
                 "time_ms": int((time.time() - t0) * 1000)}

    async def _generate_photo_captions(self, company_name: str, industry: str,
                                         master_draft_id: uuid.UUID,
                                         created_by: uuid.UUID) -> dict | None:
        """Generate photo caption copy."""
        from app.services.multi_model_content.prompt_templates import PHOTO_CAPTION_PROMPT
        prompt = PHOTO_CAPTION_PROMPT.format(
            company_info=f"{company_name} - {industry}行业企业"
        )
        content = await self._call_llm(
            "你是企业视觉内容策划师。只输出内容。",
            prompt, max_tokens=1000,
        )
        if content:
            self.db.add(ContentDerivative(
                customer_id=self.customer_id,
                source_draft_id=master_draft_id,
                derivative_type="photo_captions",
                title=f"{company_name} 实拍素材解说文案",
                body_markdown=content,
                word_count=len(content),
                generation_model="deepseek-chat",
                status="draft",
                created_by=created_by,
            ))
            await self.db.flush()
            return {"type": "photo_captions", "length": len(content)}
        return None

    async def _generate_qa_replies(self, company_name: str, industry: str,
                                     keywords: list[str], master_draft_id: uuid.UUID,
                                     created_by: uuid.UUID) -> dict | None:
        """Generate Q&A reply bank."""
        from app.services.multi_model_content.prompt_templates import QA_REPLY_PROMPT
        prompt = QA_REPLY_PROMPT.format(
            company_info=f"{company_name} - {industry} | 关键词: {', '.join(keywords[:5])}"
        )
        content = await self._call_llm(
            "你是企业客服话术专家。只输出内容。",
            prompt, max_tokens=2000,
        )
        if content:
            self.db.add(ContentDerivative(
                customer_id=self.customer_id,
                source_draft_id=master_draft_id,
                derivative_type="qa_replies",
                title=f"{company_name} 评论区答疑话术库",
                body_markdown=content,
                word_count=len(content),
                generation_model="deepseek-chat",
                status="draft",
                created_by=created_by,
            ))
            await self.db.flush()
            return {"type": "qa_replies", "length": len(content)}
        return None

    # ════════════════════════════════════════════════════════════
    # Storage helpers
    # ════════════════════════════════════════════════════════════

    async def _persist_draft(self, title: str, content: str, content_type: str,
                               created_by: uuid.UUID, keywords: list[str],
                               kb_sources: list, gap_ids: list) -> ContentDraft:
        """Persist generated content as a ContentDraft."""
        draft = ContentDraft(
            customer_id=self.customer_id,
            brief_id=None,
            generation_run_id=None,
            version=1,
            title=title,
            body_markdown=content,
            seo_metadata={
                "keywords": keywords,
                "content_type": content_type,
                "gap_ids": [str(g) for g in gap_ids],
                "generator": "EnhancedGenerationService",
            },
            word_count=len(content),
            kb_sources=[{"asset_id": str(a.id), "title": a.title} for a in kb_sources],
            status="draft",
            created_by=created_by,
        )
        self.db.add(draft)
        await self.db.flush()

        # Log generation history
        self.db.add(ContentGenerationHistory(
            customer_id=self.customer_id,
            brief_id=None,
            generation_run_id=None,
            draft_id=draft.id,
            action="generated_from_gaps",
            actor_id=created_by,
        ))
        await self.db.flush()
        return draft

    async def _auto_submit_for_review(self, draft_id: uuid.UUID,
                                        submitted_by: uuid.UUID):
        """Auto-submit draft to Agent 4 internal review queue."""
        try:
            from app.models.review import ReviewRecord, ReviewApprovalChain
            from app.models.content import ContentDraft as CD

            draft_result = await self.db.execute(
                select(CD).where(CD.id == draft_id, CD.customer_id == self.customer_id)
            )
            draft = draft_result.scalar_one_or_none()
            if not draft or draft.status != "draft":
                return None

            # Update draft status
            draft.status = "in_review"

            # Create review record
            review = ReviewRecord(
                customer_id=self.customer_id,
                draft_id=draft_id,
                stage="internal_review",
                status="pending",
            )
            self.db.add(review)
            await self.db.flush()

            # Record approval chain
            self.db.add(ReviewApprovalChain(
                customer_id=self.customer_id,
                review_record_id=review.id,
                action="auto_submitted_from_gaps",
                actor_type="system",
                actor_id=submitted_by,
                comment="从Agent3自动生成后提交审核",
            ))
            await self.db.flush()
            return review
        except Exception as e:
            print(f"[GenService] Auto-submit review failed: {e}")
            return None

    # ════════════════════════════════════════════════════════════
    # Query methods
    # ════════════════════════════════════════════════════════════

    async def get_derivatives(self, draft_id: uuid.UUID) -> list[ContentDerivative]:
        """Get all derivatives for a master draft."""
        result = await self.db.execute(
            select(ContentDerivative).where(
                ContentDerivative.customer_id == self.customer_id,
                ContentDerivative.source_draft_id == draft_id,
            ).order_by(ContentDerivative.derivative_type, ContentDerivative.created_at)
        )
        return list(result.scalars().all())

    async def get_model_variants(self, draft_id: uuid.UUID) -> dict[str, ContentDerivative]:
        """Get per-model variants keyed by target_model."""
        derivatives = await self.get_derivatives(draft_id)
        return {d.target_model: d for d in derivatives if d.target_model}

    # ════════════════════════════════════════════════════════════
    # Helpers
    # ════════════════════════════════════════════════════════════

    async def _call_llm(self, system_prompt: str, user_prompt: str,
                         max_tokens: int = 2000) -> str:
        """Call DeepSeek API."""
        client = await self._get_client()
        try:
            resp = await client.post(
                f"{self.api_base}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}",
                         "Content-Type": "application/json"},
                json={
                    "model": "deepseek-chat", "temperature": 0.7,
                    "max_tokens": max_tokens,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            return f"[生成失败: API返回{resp.status_code}]"
        except Exception as e:
            return f"[生成失败: {str(e)}]"

    def _build_kb_context(self, assets: list) -> str:
        parts = []
        for a in assets[:10]:
            parts.append(f"## {a.title}\n{a.content_text or ''}")
        return "\n\n---\n\n".join(parts) if parts else "暂无知识库资料"

    async def _get_customer(self) -> Customer:
        result = await self.db.execute(select(Customer).where(Customer.id == self.customer_id))
        c = result.scalar_one_or_none()
        if not c:
            raise NotFoundException("Customer", str(self.customer_id))
        return c

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

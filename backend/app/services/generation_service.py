"""AI content generation service — KB-sourced, LLM-powered content creation (Agent 3)."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import NotFoundException, ValidationException
from app.models.content import ContentBrief, ContentDraft, ContentGenerationRun, ContentGenerationHistory


class GenerationService:
    """Orchestrates AI content generation from briefs using KB assets as source of truth."""

    def __init__(self, db: AsyncSession, customer_id: uuid.UUID):
        self.db = db
        self.customer_id = customer_id

    async def generate(self, brief_id: uuid.UUID, user_id: uuid.UUID,
                        model_provider: str | None = None, model_name: str | None = None) -> dict:
        """Generate content for a brief using AI, sourcing from knowledge base assets."""

        # Load the brief
        from sqlalchemy import select
        result = await self.db.execute(
            select(ContentBrief).where(ContentBrief.id == brief_id, ContentBrief.customer_id == self.customer_id)
        )
        brief = result.scalar_one_or_none()
        if not brief:
            raise NotFoundException("ContentBrief", str(brief_id))

        # Load KB source assets
        from app.models.knowledge_base import KbAsset
        source_assets = []
        if brief.source_kb_asset_ids:
            result = await self.db.execute(
                select(KbAsset).where(
                    KbAsset.id.in_(brief.source_kb_asset_ids),
                    KbAsset.customer_id == self.customer_id,
                    KbAsset.is_latest == True,
                )
            )
            source_assets = result.scalars().all()

        if not source_assets:
            raise ValidationException("No valid KB source assets found. Please ensure assets exist and are published.")

        # Determine model settings
        provider = model_provider or settings.LLM_PROVIDER
        model = model_name or (settings.OPENAI_MODEL if provider == "openai" else settings.ANTHROPIC_MODEL)

        # Build the prompt from KB assets + brief params
        kb_context = self._build_kb_context(source_assets)
        system_prompt = self._build_system_prompt(brief)
        user_prompt = self._build_user_prompt(brief, kb_context)

        # Create generation run record
        run = ContentGenerationRun(
            customer_id=self.customer_id,
            brief_id=brief_id,
            status="running",
            model_provider=provider,
            model_name=model,
            prompt_text=user_prompt[:2000],  # Truncate for storage
            started_at=datetime.now(timezone.utc),
            created_by=user_id,
        )
        self.db.add(run)
        await self.db.flush()

        # Update brief status
        brief.status = "generating"

        try:
            # Call LLM
            generated_text = await self._call_llm(provider, model, system_prompt, user_prompt)

            # Create the draft
            draft = ContentDraft(
                customer_id=self.customer_id,
                brief_id=brief_id,
                generation_run_id=run.id,
                version=1,
                title=brief.title,
                body_markdown=generated_text,
                seo_metadata={"keywords": brief.target_keywords},
                word_count=len(generated_text.split()) if generated_text else 0,
                kb_sources=[{"asset_id": str(a.id), "title": a.title} for a in source_assets],
                status="draft",
                created_by=user_id,
            )
            self.db.add(draft)
            await self.db.flush()

            # Update run as completed
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
            run.tokens_output = len(generated_text.split()) if generated_text else 0

            # Record generation history
            self.db.add(ContentGenerationHistory(
                customer_id=self.customer_id,
                brief_id=brief_id,
                generation_run_id=run.id,
                draft_id=draft.id,
                action="generated",
                actor_id=user_id,
            ))

            # Update brief status
            brief.status = "ai_generated"

            return {
                "draft_id": str(draft.id),
                "version": draft.version,
                "title": draft.title,
                "body_markdown": draft.body_markdown,
                "kb_sources": draft.kb_sources,
            }

        except Exception as e:
            run.status = "failed"
            run.error_message = str(e)
            run.completed_at = datetime.now(timezone.utc)
            brief.status = "draft"
            raise ValidationException(f"Content generation failed: {str(e)}")

    def _build_kb_context(self, assets: list) -> str:
        """Build knowledge base context string from source assets."""
        parts = []
        for asset in assets:
            parts.append(f"## {asset.title}\n\n{asset.content_text or ''}")
            if asset.content_json:
                import json
                parts.append(f"\n\nStructured data:\n```json\n{json.dumps(asset.content_json, ensure_ascii=False, indent=2)}\n```")
        return "\n\n---\n\n".join(parts)

    def _build_system_prompt(self, brief) -> str:
        """Build the system prompt for content generation."""
        return f"""你是一个专业的企业内容创作助手。你必须严格基于提供的企业知识库信息进行创作，
不得编造任何企业信息、产品参数、资质案例。所有事实数据必须从知识库中提取。

内容类型: {brief.content_type}
目标受众: {brief.target_audience or '通用'}
语气风格: {brief.tone_style or '专业'}
目标字数: {brief.word_count_target or 800} 字

创作要求:
1. 所有企业信息、产品参数、资质必须从知识库100%准确提取
2. 标题必须包含核心关键词
3. 内容结构清晰，逻辑严密
4. 使用Markdown格式输出
5. 在文末列出引用的知识库来源"""

    def _build_user_prompt(self, brief, kb_context: str) -> str:
        """Build the user prompt with KB context."""
        keywords_str = ", ".join(brief.target_keywords) if brief.target_keywords else "通用"
        return f"""请基于以下企业知识库信息，创作一篇关于「{brief.title}」的内容。

核心关键词: {keywords_str}
内容描述: {brief.description or '请根据知识库信息自行组织内容'}

═══════════════════════════════════════
企业知识库（唯一信息来源）:
═══════════════════════════════════════

{kb_context}

═══════════════════════════════════════

请创作完整内容（Markdown格式），确保信息准确、逻辑清晰。"""

    async def _call_llm(self, provider: str, model: str, system_prompt: str, user_prompt: str) -> str:
        """Call the LLM provider and return generated text."""
        if provider == "openai":
            return await self._call_openai(model, system_prompt, user_prompt)
        elif provider == "anthropic":
            return await self._call_anthropic(model, system_prompt, user_prompt)
        else:
            raise ValidationException(f"Unsupported LLM provider: {provider}")

    async def _call_openai(self, model: str, system_prompt: str, user_prompt: str) -> str:
        """Call OpenAI Chat Completions API."""
        if not settings.OPENAI_API_KEY:
            raise ValidationException("OpenAI API key is not configured")

        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=3000,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise ValidationException(f"OpenAI API error: {str(e)}")

    async def _call_anthropic(self, model: str, system_prompt: str, user_prompt: str) -> str:
        """Call Anthropic Messages API."""
        if not settings.ANTHROPIC_API_KEY:
            raise ValidationException("Anthropic API key is not configured")

        try:
            from anthropic import AsyncAnthropic
            client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            response = await client.messages.create(
                model=model,
                max_tokens=3000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return response.content[0].text if response.content else ""
        except Exception as e:
            raise ValidationException(f"Anthropic API error: {str(e)}")

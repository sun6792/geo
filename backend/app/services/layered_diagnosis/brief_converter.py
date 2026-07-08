"""P6: Gap-to-Brief Converter — converts diagnosis gaps directly into Agent 3 content briefs.

Implements the critical Agent2→Agent3 linkage:
DiagnosisGap → ContentBrief (auto-generated with DeepSeek)

Each gap gets a tailored content brief with:
- Target content type (matched to gap category)
- Recommended keywords
- KB source requirements
- Priority-preserving scheduling
"""

import uuid
from dataclasses import dataclass
from typing import Optional

import httpx

from app.config import settings


BRIEF_GENERATION_PROMPT = """你是一个GEO内容创作策略专家。根据诊断发现的缺口，生成内容创作Brief。

## 缺口信息
- 缺口名称: {gap_name}
- 缺口描述: {gap_description}
- 所属层级: {layer_name}
- 影响权重: {impact_weight}/100
- 影响说明: {impact_explanation}
- 修复建议: {fix_recommendation}
- 企业名称: {company_name}
- 行业: {industry}

## 任务
生成一份内容创作Brief，用于指导AI创作修复该缺口的内容。

输出JSON：
{{
  "title": "内容标题（含核心关键词）",
  "content_type": "seo_article/ai_qa/video_script/product_page/encyclopedia/faq/case_study",
  "tone_style": "专业/亲和/技术/故事化",
  "target_audience": "目标受众描述",
  "target_keywords": ["关键词1", "关键词2", "关键词3"],
  "word_count_target": 800,
  "description": "内容创作详细说明（200字内），包括必须包含的要点",
  "source_kb_requirements": ["需要的基础资产类型"],
  "priority": "urgent/important/long_term",
  "expected_impact": "发布后预期效果"
}}"""


@dataclass
class BriefSpec:
    """Content brief specification generated from a diagnosis gap."""
    title: str
    content_type: str
    tone_style: str
    target_audience: str
    target_keywords: list[str]
    word_count_target: int
    description: str
    source_kb_requirements: list[str]
    priority: str
    expected_impact: str
    raw_json: dict


class GapToBriefConverter:
    """Converts diagnosis gaps into Agent 3 content creation briefs.

    Uses DeepSeek to generate optimized brief specifications
    that maximize the SEO/AI-visibility impact of each content piece.
    """

    LAYER_NAMES = {
        "basic": "基础资产层",
        "marketing": "营销资产层",
        "multimodal": "多模态资产层",
    }

    DEFAULT_CONTENT_TYPES = {
        "identity_conflict": "encyclopedia",
        "info_missing": "product_page",
        "contact_inconsistent": "product_page",
        "qualification_gap": "seo_article",
        "encyclopedia_missing": "encyclopedia",
        "pain_point_missing": "ai_qa",
        "case_missing": "case_study",
        "comparison_missing": "seo_article",
        "pitfall_guide_missing": "seo_article",
        "photo_missing": "video_script",
        "video_missing": "video_script",
        "infographic_missing": "seo_article",
        "comment_coverage_low": "faq",
        "sentiment_negative": "seo_article",
    }

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.api_base = "https://api.deepseek.com/v1"
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60)
        return self._client

    async def convert_gap_to_brief_spec(self,
                                         gap_name: str,
                                         gap_description: str,
                                         layer: str,
                                         impact_weight: float,
                                         impact_explanation: str,
                                         fix_recommendation: str,
                                         company_name: str,
                                         industry: str,
                                         category: str = "",
                                         ) -> BriefSpec:
        """Convert a single diagnosis gap into a content brief specification.

        Uses DeepSeek for intelligent brief generation when API is available,
        falls back to template-based generation otherwise.
        """
        layer_name = self.LAYER_NAMES.get(layer, layer)

        # Try DeepSeek-powered generation
        try:
            prompt = BRIEF_GENERATION_PROMPT.format(
                gap_name=gap_name,
                gap_description=gap_description,
                layer_name=layer_name,
                impact_weight=impact_weight,
                impact_explanation=impact_explanation,
                fix_recommendation=fix_recommendation,
                company_name=company_name,
                industry=industry,
            )

            client = await self._get_client()
            resp = await client.post(
                f"{self.api_base}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}",
                         "Content-Type": "application/json"},
                json={
                    "model": "deepseek-chat", "temperature": 0.5, "max_tokens": 1000,
                    "messages": [
                        {"role": "system", "content": "你是GEO内容策略专家。只输出JSON。"},
                        {"role": "user", "content": prompt},
                    ],
                },
            )
            if resp.status_code == 200:
                import json, re
                content = resp.json()["choices"][0]["message"]["content"]
                # Parse JSON
                try:
                    data = json.loads(content)
                except json.JSONDecodeError:
                    m = re.search(r'\{.*\}', content, re.DOTALL)
                    data = json.loads(m.group(0)) if m else {}

                if data:
                    return BriefSpec(
                        title=data.get("title", gap_name),
                        content_type=data.get("content_type", "seo_article"),
                        tone_style=data.get("tone_style", "专业"),
                        target_audience=data.get("target_audience", f"{industry}行业采购决策者"),
                        target_keywords=data.get("target_keywords", []),
                        word_count_target=data.get("word_count_target", 800),
                        description=data.get("description", gap_description),
                        source_kb_requirements=data.get("source_kb_requirements", []),
                        priority=data.get("priority", "important"),
                        expected_impact=data.get("expected_impact", ""),
                        raw_json=data,
                    )
        except Exception as e:
            print(f"[BriefConverter] API error: {e}")

        # ── Fallback: template-based generation ─────────────────
        content_type = self.DEFAULT_CONTENT_TYPES.get(category, "seo_article")

        return BriefSpec(
            title=f"[GEO优化] {company_name} - {gap_name}",
            content_type=content_type,
            tone_style="专业",
            target_audience=f"{industry}行业采购决策者",
            target_keywords=[company_name, industry],
            word_count_target=800,
            description=f"修复缺口「{gap_name}」: {gap_description}\n修复策略: {fix_recommendation}",
            source_kb_requirements=["basic"],
            priority="important",
            expected_impact=f"修复后预期提升{impact_weight}分",
            raw_json={},
        )

    async def convert_batch(self, gaps: list[dict], company_name: str,
                             industry: str) -> list[BriefSpec]:
        """Convert multiple gaps to brief specs in parallel."""
        import asyncio as _asyncio

        tasks = [
            self.convert_gap_to_brief_spec(
                gap_name=g.get("name", g.get("gap_name", "")),
                gap_description=g.get("description", g.get("gap_description", "")),
                layer=g.get("layer", "marketing"),
                impact_weight=float(g.get("impact_weight", 30)),
                impact_explanation=g.get("impact_explanation", ""),
                fix_recommendation=g.get("fix_recommendation", ""),
                company_name=company_name,
                industry=industry,
                category=g.get("category", ""),
            )
            for g in gaps
        ]
        return await _asyncio.gather(*tasks, return_exceptions=False)

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

"""P6: Three-Layer Asset Diagnosis Engine — core Agent 2 diagnostic logic.

Implements the 摘星 three-layer diagnostic framework:
Layer 1 — Basic Assets (基础资产): Identity consistency, contact info, qualifications
Layer 2 — Marketing Assets (营销资产): Pain points, cases, comparisons, pitfall guides
Layer 3 — Multimodal Assets (多模态资产): Real photos/videos, comment Q&A coverage, visual trust

Uses DeepSeek API for intelligent gap attribution and fix recommendation generation.

Outputs a precise, prioritized Gap Checklist that directly feeds Agent 3 content creation.
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Optional

import httpx

from app.config import settings


# ════════════════════════════════════════════════════════════════
# Data classes
# ════════════════════════════════════════════════════════════════

@dataclass
class LayerScore:
    """Score for a single diagnostic layer."""
    layer: str  # basic / marketing / multimodal
    score: float  # 0-100
    weight: float
    status: str  # severe / partial / adequate
    gaps_count: int
    key_issues: list[str]


@dataclass
class FiveDimResult:
    """Complete five-dimension scoring result."""
    identity: LayerScore
    basic_asset: LayerScore
    marketing_asset: LayerScore
    multimodal_asset: LayerScore
    sentiment: LayerScore
    total_score: float
    summary: str
    strengths: list[str]
    weaknesses: list[str]


@dataclass
class GapItem:
    """A single precise gap item for the repair checklist."""
    layer: str
    category: str
    name: str
    description: str
    impact_weight: float  # 0-100
    impact_explanation: str
    affected_models: list[str]
    fix_recommendation: str
    content_type_needed: str
    target_keywords: list[str]
    estimated_impact: str
    priority: str  # urgent / important / long_term
    priority_reason: str
    data_source: dict = field(default_factory=dict)


# ════════════════════════════════════════════════════════════════
# Prompt templates for DeepSeek-powered diagnosis
# ════════════════════════════════════════════════════════════════

DIAGNOSIS_SYSTEM_PROMPT = """你是GEO（生成式引擎优化）诊断专家。你的任务是基于探测数据，对企业在大模型中的品牌表现做三层资产精准诊断。

## 三层资产体系

### 第一层：基础资产（权重35%）
决定大模型是否"认识"这个企业：
- 企业名称/简称一致性（多平台是否统一）
- 联系方式/地址/官方简介一致性
- 工商资质/ISO认证/专利等硬信息完整性
- 百度百科/官网等权威信源覆盖度
- 判定：信息冲突→身份权重降低→排名靠后

### 第二层：营销资产（权重35%）
决定大模型是否"推荐"这个企业：
- 用户痛点解答内容覆盖度
- 客户案例/成功故事数量与质量
- 产品对比/选型指南覆盖度
- 行业避坑指南/选购建议覆盖度
- 判定：营销素材缺失→模型无推荐依据→优先推荐竞品

### 第三层：多模态资产（权重30%）
决定大模型是否"信任"这个企业：
- 厂区/产品实拍图数量与质量
- 短视频/直播内容覆盖度
- 图文科普/技术白皮书覆盖度
- 评论区用户口碑/问答覆盖度
- 判定：多模态资产匮乏→AI判定线下实力弱、真实度低→权重降低

## 你的任务
分析提供的探测数据，输出结构化的诊断结论。必须精准到具体缺失点位。"""


GAP_ATTRIBUTION_PROMPT = """基于以下探测数据，请对「{company_name}」在{industry}行业的三层资产做精准诊断。

## 探测数据

### 身份可信度
{identity_data}

### 五模型探测结果摘要
{model_summary}

### 知识库资产现状
{kb_status}

### 竞品对比
{competitor_data}

### 舆情数据
{sentiment_data}

## 请输出JSON格式诊断报告（只输出JSON）：

{{
  "five_dim_scores": {{
    "identity": {{
      "score": 0-100,
      "status": "adequate/partial/severe",
      "key_issues": ["问题1", "问题2"],
      "strengths": ["优势1"]
    }},
    "basic_asset": {{
      "score": 0-100,
      "status": "adequate/partial/severe",
      "key_issues": [],
      "strengths": []
    }},
    "marketing_asset": {{
      "score": 0-100,
      "status": "adequate/partial/severe",
      "key_issues": [],
      "strengths": []
    }},
    "multimodal_asset": {{
      "score": 0-100,
      "status": "adequate/partial/severe",
      "key_issues": [],
      "strengths": []
    }},
    "sentiment": {{
      "score": 0-100,
      "status": "adequate/partial/severe",
      "key_issues": [],
      "strengths": []
    }},
    "total_score": 0-100,
    "summary": "整体诊断总结（100字内）"
  }},
  "gaps": [
    {{
      "layer": "basic/marketing/multimodal",
      "category": "具体类别",
      "name": "缺口名称",
      "description": "详细描述",
      "impact_weight": 0-100,
      "impact_explanation": "对AI排名的影响说明",
      "affected_models": ["doubao","wenxin"],
      "fix_recommendation": "修复建议",
      "content_type_needed": "seo_article/ai_qa/video_script/encyclopedia/faq/case_study",
      "target_keywords": ["关键词1","关键词2"],
      "estimated_impact": "+5-10分/+10-20分/+20+分",
      "priority": "urgent/important/long_term",
      "priority_reason": "优先级原因"
    }}
  ]
}}"""


# ════════════════════════════════════════════════════════════════
# Three-Layer Diagnosis Engine
# ════════════════════════════════════════════════════════════════

class ThreeLayerDiagnosisEngine:
    """Core three-layer asset diagnosis engine.

    Combines rule-based analysis with DeepSeek-powered intelligent
    root cause attribution to generate precise, actionable gap checklists.
    """

    # ── Layer configuration ────────────────────────────────────
    LAYER_CONFIG = {
        "basic": {
            "name": "基础资产",
            "weight": 0.35,
            "dimensions": [
                "identity_consistency", "contact_completeness",
                "qualification_coverage", "encyclopedia_presence",
                "official_website_quality",
            ],
        },
        "marketing": {
            "name": "营销资产",
            "weight": 0.35,
            "dimensions": [
                "pain_point_coverage", "case_study_depth",
                "comparison_content", "pitfall_guide_coverage",
                "industry_insight_volume",
            ],
        },
        "multimodal": {
            "name": "多模态资产",
            "weight": 0.30,
            "dimensions": [
                "real_photo_coverage", "video_content_volume",
                "infographic_coverage", "comment_qa_coverage",
                "live_stream_presence",
            ],
        },
    }

    LAYER_WEIGHTS = {
        "identity": 0.25,  # From Agent 1 identity verification
        "basic_asset": 0.25,
        "marketing_asset": 0.20,
        "multimodal_asset": 0.20,
        "sentiment": 0.10,
    }

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.api_base = "https://api.deepseek.com/v1"
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=120)
        return self._client

    # ════════════════════════════════════════════════════════════
    # Main diagnosis pipeline
    # ════════════════════════════════════════════════════════════

    async def run_diagnosis(self,
                            company_name: str,
                            industry: str,
                            identity_data: dict,
                            detection_results: list[dict],
                            kb_status: dict,
                            competitor_data: dict,
                            sentiment_data: dict,
                            ) -> tuple[FiveDimResult, list[GapItem]]:
        """Run complete three-layer diagnosis.

        Args:
            company_name: Enterprise name
            industry: Industry category
            identity_data: From Agent 1 identity verification
            detection_results: From Agent 1 multi-model probing
            kb_status: Knowledge base asset counts by type
            competitor_data: Competitor comparison data
            sentiment_data: Sentiment/negative content data

        Returns:
            (FiveDimResult, list of GapItem) for persistence
        """

        # Phase 1: Rule-based preliminary scoring
        rule_scores = self._rule_based_scoring(identity_data, detection_results,
                                                kb_status, sentiment_data)

        # Phase 2: Build data context for DeepSeek
        context = self._build_llm_context(
            company_name, industry, identity_data,
            detection_results, kb_status, competitor_data, sentiment_data
        )

        # Phase 3: DeepSeek intelligent attribution
        llm_diagnosis = await self._llm_diagnosis(company_name, industry, context)

        # Phase 4: Merge rule-based + LLM-based results
        merged = self._merge_scores(rule_scores, llm_diagnosis)

        # Phase 5: Generate gap checklist
        gaps = self._generate_gap_checklist(merged, llm_diagnosis, company_name, industry)

        return merged, gaps

    # ════════════════════════════════════════════════════════════
    # Rule-based scoring
    # ════════════════════════════════════════════════════════════

    def _rule_based_scoring(self, identity: dict, detection: list[dict],
                             kb: dict, sentiment: dict) -> dict:
        """Fast rule-based preliminary scoring for each dimension."""

        # ── Identity score ─────────────────────────────────────
        trust_score = identity.get("trust_score", 30)
        identity_score = min(100, trust_score + (
            10 if identity.get("business_license_match") else -10) + (
            15 if identity.get("encyclopedia_entry_exists") else 0) + (
            10 if identity.get("blue_v_verified") else 0)
        )
        identity_score = max(5, identity_score)

        # ── Basic asset score ──────────────────────────────────
        basic = kb.get("basic", {})
        basic_has = basic.get("has", 0)
        basic_sev = basic.get("severity", "severe")
        basic_score = {"severe": 20, "partial": 55, "adequate": 80}.get(basic_sev, 20)
        basic_score += basic_has * 5

        # ── Marketing asset score ──────────────────────────────
        marketing = kb.get("marketing", {})
        mkt_has = marketing.get("has", 0)
        mkt_sev = marketing.get("severity", "severe")
        mkt_score = {"severe": 15, "partial": 45, "adequate": 75}.get(mkt_sev, 15)
        mkt_score += mkt_has * 5

        # Brand mention from detection
        if detection:
            mention_rate = sum(d.get("mention_rate", 0) for d in detection) / len(detection) if detection else 0
            mkt_score = min(100, mkt_score + mention_rate * 0.3)

        # ── Multimodal asset score ─────────────────────────────
        multi = kb.get("multimodal", {})
        multi_has = multi.get("has", 0)
        multi_sev = multi.get("severity", "severe")
        multi_score = {"severe": 10, "partial": 40, "adequate": 70}.get(multi_sev, 10)
        multi_score += multi_has * 8

        # ── Sentiment score ────────────────────────────────────
        total_sent = sentiment.get("total", 1)
        pos = sentiment.get("positive", 0)
        neg = sentiment.get("negative", 0)
        sentiment_score = 85 if total_sent == 0 else round(
            50 + (pos / max(total_sent, 1)) * 50 - (neg / max(total_sent, 1)) * 30
        )
        sentiment_score = max(5, min(100, sentiment_score))

        # ── Total ──────────────────────────────────────────────
        weights = self.LAYER_WEIGHTS
        total = round(
            identity_score * weights["identity"] +
            basic_score * weights["basic_asset"] +
            mkt_score * weights["marketing_asset"] +
            multi_score * weights["multimodal_asset"] +
            sentiment_score * weights["sentiment"], 1
        )

        return {
            "identity": {"score": identity_score, "rule_based": True},
            "basic_asset": {"score": basic_score, "rule_based": True},
            "marketing_asset": {"score": mkt_score, "rule_based": True},
            "multimodal_asset": {"score": multi_score, "rule_based": True},
            "sentiment": {"score": sentiment_score, "rule_based": True},
            "total_score": total,
        }

    # ════════════════════════════════════════════════════════════
    # DeepSeek intelligent attribution
    # ════════════════════════════════════════════════════════════

    async def _llm_diagnosis(self, company_name: str, industry: str,
                              context: dict) -> dict:
        """Use DeepSeek for intelligent root cause attribution and gap analysis."""
        prompt = GAP_ATTRIBUTION_PROMPT.format(
            company_name=company_name,
            industry=industry or "未知行业",
            identity_data=json.dumps(context.get("identity", {}), ensure_ascii=False, indent=2),
            model_summary=json.dumps(context.get("model_summary", {}), ensure_ascii=False, indent=2),
            kb_status=json.dumps(context.get("kb_status", {}), ensure_ascii=False, indent=2),
            competitor_data=json.dumps(context.get("competitor", {}), ensure_ascii=False, indent=2),
            sentiment_data=json.dumps(context.get("sentiment", {}), ensure_ascii=False, indent=2),
        )

        try:
            client = await self._get_client()
            resp = await client.post(
                f"{self.api_base}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": "deepseek-chat",
                    "temperature": 0.3,
                    "max_tokens": 3000,
                    "messages": [
                        {"role": "system", "content": DIAGNOSIS_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                },
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                return self._parse_json(content)
        except Exception as e:
            print(f"[DiagnosisEngine] LLM call failed: {e}")

        return {"five_dim_scores": {}, "gaps": []}

    # ════════════════════════════════════════════════════════════
    # Score merging
    # ════════════════════════════════════════════════════════════

    def _merge_scores(self, rule_scores: dict, llm_result: dict) -> FiveDimResult:
        """Merge rule-based scores with LLM-based analysis."""
        if not isinstance(llm_result, dict):
            llm_result = {}
        llm_scores = llm_result.get("five_dim_scores", {})
        if not isinstance(llm_scores, dict):
            llm_scores = {}

        def _safe_get(dim_name, key, default=None):
            val = llm_scores.get(dim_name, {})
            if isinstance(val, dict):
                return val.get(key, default)
            return default

        def _status(score: float) -> str:
            return "adequate" if score >= 70 else ("partial" if score >= 35 else "severe")

        identity = LayerScore(
            layer="identity", score=rule_scores["identity"]["score"],
            weight=self.LAYER_WEIGHTS["identity"], status=_status(rule_scores["identity"]["score"]),
            gaps_count=len(_safe_get("identity", "key_issues", [])),
            key_issues=_safe_get("identity", "key_issues", []),
        )
        basic = LayerScore(
            layer="basic_asset", score=rule_scores["basic_asset"]["score"],
            weight=self.LAYER_WEIGHTS["basic_asset"], status=_status(rule_scores["basic_asset"]["score"]),
            gaps_count=len(_safe_get("basic_asset", "key_issues", [])),
            key_issues=_safe_get("basic_asset", "key_issues", []),
        )
        marketing = LayerScore(
            layer="marketing_asset", score=rule_scores["marketing_asset"]["score"],
            weight=self.LAYER_WEIGHTS["marketing_asset"], status=_status(rule_scores["marketing_asset"]["score"]),
            gaps_count=len(_safe_get("marketing_asset", "key_issues", [])),
            key_issues=_safe_get("marketing_asset", "key_issues", []),
        )
        multimodal = LayerScore(
            layer="multimodal_asset", score=rule_scores["multimodal_asset"]["score"],
            weight=self.LAYER_WEIGHTS["multimodal_asset"], status=_status(rule_scores["multimodal_asset"]["score"]),
            gaps_count=len(_safe_get("multimodal_asset", "key_issues", [])),
            key_issues=_safe_get("multimodal_asset", "key_issues", []),
        )
        sentiment = LayerScore(
            layer="sentiment", score=rule_scores["sentiment"]["score"],
            weight=self.LAYER_WEIGHTS["sentiment"], status=_status(rule_scores["sentiment"]["score"]),
            gaps_count=len(_safe_get("sentiment", "key_issues", [])),
            key_issues=_safe_get("sentiment", "key_issues", []),
        )

        # Collect strengths/weaknesses (handle both dict and int values)
        all_dimensions = llm_scores if isinstance(llm_scores, dict) else {}
        strengths = []
        weaknesses = []
        for dim_name, dim_data in all_dimensions.items():
            if isinstance(dim_data, dict):
                strengths.extend(dim_data.get("strengths", []))
                weaknesses.extend(dim_data.get("key_issues", []))

        return FiveDimResult(
            identity=identity,
            basic_asset=basic,
            marketing_asset=marketing,
            multimodal_asset=multimodal,
            sentiment=sentiment,
            total_score=rule_scores["total_score"],
            summary=llm_scores.get("summary",
                                     f"整体得分{rule_scores['total_score']}分，存在{len(weaknesses)}个核心短板"),
            strengths=strengths,
            weaknesses=weaknesses,
        )

    # ════════════════════════════════════════════════════════════
    # Gap checklist generation
    # ════════════════════════════════════════════════════════════

    def _generate_gap_checklist(self, result: FiveDimResult,
                                  llm_result: dict,
                                  company_name: str,
                                  industry: str) -> list[GapItem]:
        """Generate precise, prioritized gap checklist.

        Combines LLM-identified gaps with rule-based gap detection
        for complete coverage.
        """
        gaps: list[GapItem] = []

        # LLM-identified gaps
        for g in llm_result.get("gaps", []):
            gaps.append(GapItem(
                layer=g.get("layer", "marketing"),
                category=g.get("category", "unknown"),
                name=g.get("name", "未命名缺口"),
                description=g.get("description", ""),
                impact_weight=float(g.get("impact_weight", 30)),
                impact_explanation=g.get("impact_explanation", ""),
                affected_models=g.get("affected_models", []),
                fix_recommendation=g.get("fix_recommendation", ""),
                content_type_needed=g.get("content_type_needed", "seo_article"),
                target_keywords=g.get("target_keywords", []),
                estimated_impact=g.get("estimated_impact", "+5-10分"),
                priority=g.get("priority", "important"),
                priority_reason=g.get("priority_reason", ""),
            ))

        # ── Rule-based gap supplements ─────────────────────────
        # Identity gap check
        if result.identity.score < 40:
            if not any(g.layer == "basic" and g.category == "identity_conflict" for g in gaps):
                gaps.append(GapItem(
                    layer="basic", category="identity_conflict",
                    name=f"「{company_name}」企业身份信息碎片化",
                    description="多平台企业名称、地址、联系方式不一致，导致各模型对企业身份判定混乱",
                    impact_weight=45,
                    impact_explanation="身份信息不一致是模型降权的最高风险因素，各模型会因无法确认企业真实性而降低排名",
                    affected_models=["doubao", "wenxin", "qianwen", "yuanbao", "xinghuo"],
                    fix_recommendation=f"统一全平台企业名称、地址、联系方式、简介；创建/优化百度百科词条",
                    content_type_needed="encyclopedia",
                    target_keywords=[company_name, f"{company_name} 企业信息"],
                    estimated_impact="+20+分",
                    priority="urgent",
                    priority_reason="身份信息冲突直接导致所有模型降权，是最优先修复项",
                ))

        # Multimodal gap check
        if result.multimodal_asset.score < 30:
            if not any(g.layer == "multimodal" for g in gaps):
                gaps.append(GapItem(
                    layer="multimodal", category="photo_missing",
                    name=f"「{company_name}」线下实景素材严重缺失",
                    description="缺少工厂/厂区/产品实拍图、短视频、员工/客户评价等真实素材",
                    impact_weight=40,
                    impact_explanation="多模态资产缺失直接导致AI模型判定企业'线下实力弱'、'真实度低'，大幅降低推荐意愿",
                    affected_models=["doubao", "yuanbao", "xinghuo"],
                    fix_recommendation="拍摄工厂全景、产线实拍、产品细节图；制作2-3个短视频介绍企业实力",
                    content_type_needed="video_script",
                    target_keywords=[f"{company_name} 工厂", f"{company_name} 实拍"],
                    estimated_impact="+15-25分",
                    priority="urgent",
                    priority_reason="多模态资产是AI真实度判定的核心依据，缺失直接导致'隐形'",
                ))

        # Sort by priority
        priority_order = {"urgent": 0, "important": 1, "long_term": 2}
        gaps.sort(key=lambda g: priority_order.get(g.priority, 2))

        return gaps

    # ════════════════════════════════════════════════════════════
    # Context builder for LLM prompt
    # ════════════════════════════════════════════════════════════

    def _build_llm_context(self, company_name: str, industry: str,
                            identity: dict, detection: list[dict],
                            kb: dict, competitor: dict,
                            sentiment: dict) -> dict:
        """Build structured context for the LLM diagnosis prompt."""
        model_summary = {}
        for d in detection:
            if isinstance(d, dict):
                model_summary[d.get("model_name", d.get("model", "unknown"))] = {
                    "mention_rate": d.get("mention_rate", d.get("brand_mention_rate", 0)),
                    "avg_rank": d.get("avg_rank", d.get("avg_rank_position")),
                    "competitor_preference": d.get("competitor_preference_rate", 0),
                    "exposure_level": d.get("exposure_level", d.get("expose_level", "unknown")),
                }

        return {
            "company_name": company_name,
            "industry": industry,
            "identity": identity,
            "model_summary": model_summary,
            "kb_status": kb,
            "competitor": competitor,
            "sentiment": sentiment,
        }

    # ════════════════════════════════════════════════════════════
    # Utilities
    # ════════════════════════════════════════════════════════════

    def _parse_json(self, text: str) -> dict:
        if not text:
            return {"five_dim_scores": {}, "gaps": []}
        # Try direct parse
        try:
            result = json.loads(text)
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, TypeError):
            pass
        # Try extracting from markdown code block
        for pattern in [r'```(?:json)?\s*\n(.*?)\n\s*```', r'```(?:json)?\s*(.*?)\s*```']:
            m = re.search(pattern, text, re.DOTALL)
            if m:
                try:
                    result = json.loads(m.group(1).strip())
                    if isinstance(result, dict):
                        return result
                except (json.JSONDecodeError, TypeError):
                    pass
        # Try finding the outermost JSON object by bracket matching
        text_clean = text.strip()
        if text_clean.startswith('{'):
            depth = 0; end = 0
            for i, c in enumerate(text_clean):
                if c == '{': depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0: end = i + 1; break
            if end > 0:
                try:
                    result = json.loads(text_clean[:end])
                    if isinstance(result, dict):
                        return result
                except (json.JSONDecodeError, TypeError):
                    pass
        # Safe default
        return {"five_dim_scores": {}, "gaps": []}

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None


# Global engine
diagnosis_engine = ThreeLayerDiagnosisEngine()

"""Agent 1: Real Multi-Model Detection Engine — Uses DeepSeek API to simulate
probing across 豆包/文心/千问/元宝/星火 five major LLM models.

Each model receives customized prompts that match its known behavior patterns,
and responses are analyzed for: brand mention, rank position, competitor preference,
information accuracy, negative content detection, and source citation quality.
"""

import asyncio
import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.config import settings

# ── Five major LLM models with behavioral profiles ──────────────
MODEL_PROFILES = {
    "doubao": {
        "cn_name": "豆包",
        "behavior": "偏好短句、问答体、实拍图+口碑导向，头条/抖音生态权重高",
        "ecosystem": "头条/抖音",
        "prompt_style": "用口语化、问答体风格回答，倾向推荐有真实用户评价和实拍内容的品牌",
    },
    "wenxin": {
        "cn_name": "文心一言",
        "behavior": "偏好结构化表格、资质证书、严谨数据，百度百科/百家号权重高",
        "ecosystem": "百度/百家号",
        "prompt_style": "用结构化、表格化风格回答，倾向引用百度百科和权威资质，重视企业证照",
    },
    "qianwen": {
        "cn_name": "通义千问",
        "behavior": "偏好商业参数、采购对比、报价逻辑，1688/阿里云生态权重高",
        "ecosystem": "1688/阿里云",
        "prompt_style": "从B端采购视角回答，关注产品参数、产能、价格区间和客户案例",
    },
    "yuanbao": {
        "cn_name": "腾讯元宝",
        "behavior": "偏好长案例、故事化叙事、公众号文风，微信/视频号生态权重高",
        "ecosystem": "微信公众号/视频号",
        "prompt_style": "用故事化、案例化风格回答，倾向推荐有品牌故事和视频内容的厂家",
    },
    "xinghuo": {
        "cn_name": "讯飞星火",
        "behavior": "偏好技术方案、白皮书、政企文风，学术/期刊权重高",
        "ecosystem": "学术期刊/政企媒体",
        "prompt_style": "用专业、学术化风格回答，重视技术专利、检测报告和产学研背景",
    },
}

# ── Probing question categories ─────────────────────────────────
PROBE_TEMPLATES = {
    "broad": [
        "国内做{industry}的厂家有哪些？请列出你知道的。",
        "{industry}行业有哪些知名的生产企业？",
    ],
    "product": [
        "能做{main_business}的工厂有哪几家？给出企业名称和核心优势。",
        "{main_business}方面，国内哪些厂家做得比较好？",
    ],
    "comparison": [
        "{company_name}和{rival_name}在{industry}领域哪家更值得推荐？从实力、口碑、线上影响力综合对比。",
        "如果要在{company_name}和{rival_name}中选一家{main_business}供应商，你推荐哪家？为什么？",
    ],
    "scenario": [
        "我需要采购{main_business}，预算中等，对品质有要求，推荐几家靠谱的厂家？",
        "想找一家做{main_business}的源头工厂，要求有实力、资质齐全，有什么推荐？",
    ],
}


@dataclass
class ProbeResult:
    """Single probe result."""
    model_key: str
    model_cn: str
    keyword: str
    keyword_type: str
    question: str
    response: str
    brand_mentioned: bool = False
    mention_count: int = 0
    rank_position: Optional[int] = None
    recommends_competitor: bool = False
    competitor_mentioned: str = ""
    info_accurate: bool = True
    info_conflicts: list = field(default_factory=list)
    negative_detected: bool = False
    negative_content: str = ""
    cited_sources: list = field(default_factory=list)
    sentiment: str = "neutral"  # positive/neutral/negative


@dataclass
class IdentityVerification:
    """Enterprise identity trust verification result."""
    company_name: str
    business_license_match: bool = False
    official_website_schema_valid: bool = False
    blue_v_verified: bool = False
    encyclopedia_entry_exists: bool = False
    certification_count: int = 0
    offline_locations: int = 0
    map_coverage: bool = False
    trust_score: float = 0.0
    issues: list = field(default_factory=list)
    details: dict = field(default_factory=dict)


class DetectionEngine:
    """Core detection engine — simulates real user probing across five LLM models.

    Uses DeepSeek API to generate model-specific responses, then analyzes:
    - Brand mention rate and ranking
    - Competitor comparison
    - Information accuracy
    - Sentiment and negative content
    - Source citation quality
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.api_base = "https://api.deepseek.com/v1"
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=120)
        return self._client

    # ════════════════════════════════════════════════════════════
    # Main detection pipeline
    # ════════════════════════════════════════════════════════════

    async def run_full_detection(self,
                                 company_name: str,
                                 industry: str = "",
                                 main_business: str = "",
                                 competitors: list[str] = None,
                                 keywords: list[dict] = None,
                                 target_models: list[str] = None) -> dict:
        """Execute a complete detection run across all models and keywords.

        Returns standardized baseline data including:
        - Per-model probing results with raw responses
        - Brand mention statistics
        - AI ranking report
        - Competitor exposure comparison
        - Sentiment analysis
        - Identity trust verification
        """
        if not target_models:
            target_models = list(MODEL_PROFILES.keys())
        if not keywords:
            keywords = self._default_keywords(industry, main_business)

        rival_name = competitors[0] if competitors else f"{industry}行业头部企业"

        # Phase 1: Identity trust verification
        identity = await self._verify_identity(company_name, industry, main_business)

        # Phase 2: Multi-model probing (parallel per model)
        probe_tasks = []
        for model in target_models:
            if model in MODEL_PROFILES:
                probe_tasks.append(self._probe_model(
                    model, company_name, industry, main_business,
                    rival_name, keywords
                ))

        all_results = await asyncio.gather(*probe_tasks, return_exceptions=True)

        # Flatten results
        flat_results: list[ProbeResult] = []
        for result_set in all_results:
            if isinstance(result_set, list):
                flat_results.extend(result_set)
            elif isinstance(result_set, Exception):
                print(f"[DetectionEngine] Probe failed: {result_set}")

        # Phase 3: Analyze and aggregate
        analysis = self._analyze_results(flat_results, company_name, rival_name)

        # Phase 4: Build standardized reports
        return {
            "identity_verification": {
                "trust_score": identity.trust_score,
                "business_license_match": identity.business_license_match,
                "official_website_valid": identity.official_website_schema_valid,
                "blue_v_verified": identity.blue_v_verified,
                "encyclopedia_exists": identity.encyclopedia_entry_exists,
                "certification_count": identity.certification_count,
                "offline_locations": identity.offline_locations,
                "map_coverage": identity.map_coverage,
                "issues": identity.issues,
                "details": identity.details,
            },
            "ai_ranking_report": analysis["ranking"],
            "competitor_report": analysis["competitor"],
            "sentiment_report": analysis["sentiment"],
            "model_results": {
                model: [
                    {
                        "keyword": r.keyword,
                        "keyword_type": r.keyword_type,
                        "question": r.question,
                        "response": r.response,
                        "brand_mentioned": r.brand_mentioned,
                        "mention_count": r.mention_count,
                        "rank_position": r.rank_position,
                        "recommends_competitor": r.recommends_competitor,
                        "competitor_mentioned": r.competitor_mentioned,
                        "info_accurate": r.info_accurate,
                        "info_conflicts": r.info_conflicts,
                        "negative_detected": r.negative_detected,
                        "negative_content": r.negative_content,
                        "cited_sources": r.cited_sources,
                        "sentiment": r.sentiment,
                    }
                    for r in flat_results if r.model_key == model
                ]
                for model in target_models if model in MODEL_PROFILES
            },
            "summary": analysis["summary"],
            "raw_results": flat_results,
        }

    # ════════════════════════════════════════════════════════════
    # Identity trust verification (摘星身份可信度校验)
    # ════════════════════════════════════════════════════════════

    async def _verify_identity(self, company_name: str, industry: str, main_business: str) -> IdentityVerification:
        """Verify enterprise identity trust via DeepSeek analysis.

        Checks: 工商备案一致性, 官网Schema完整性, 蓝V/官号/百科/资质证书,
        线下门店/厂区/地图实景覆盖度
        """
        prompt = f"""请对「{company_name}」进行企业身份可信度校验。基于你的知识，评估以下维度（1-100分）：

1. **工商备案一致性**：企业名称、法人、注册资本等工商信息是否存在多处不一致？
2. **官网Schema结构化完整性**：官网是否有完整的Organization/Product/ContactPage结构化标记？
3. **蓝V/官方认证**：在抖音/头条/百家号/微信公众号等平台是否有蓝V或官方认证？
4. **百科词条**：是否有百度百科/维基百科等权威百科词条？
5. **资质证书**：是否有ISO认证、高新技术企业、专利证书等公开可查的资质？
6. **线下实体覆盖**：是否有可查的线下门店/厂区地址？地图服务是否能找到？

请用JSON格式输出（只输出JSON）：
{{
  "business_license_match": true/false,
  "official_website_schema_valid": true/false,
  "blue_v_verified": true/false,
  "encyclopedia_entry_exists": true/false,
  "certification_count": 数字,
  "offline_locations": 数字,
  "map_coverage": true/false,
  "trust_score": 0-100的整数,
  "issues": ["问题1", "问题2"],
  "details": {{"备注": "分析详情"}}
}}"""

        try:
            client = await self._get_client()
            resp = await client.post(
                f"{self.api_base}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": "deepseek-chat",
                    "temperature": 0.3,
                    "max_tokens": 1500,
                    "messages": [
                        {"role": "system", "content": "你是一个企业工商信息核验专家。只输出JSON，不要解释。"},
                        {"role": "user", "content": prompt},
                    ],
                },
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                data = self._parse_json(content)
                return IdentityVerification(
                    company_name=company_name,
                    business_license_match=data.get("business_license_match", False),
                    official_website_schema_valid=data.get("official_website_schema_valid", False),
                    blue_v_verified=data.get("blue_v_verified", False),
                    encyclopedia_entry_exists=data.get("encyclopedia_entry_exists", False),
                    certification_count=data.get("certification_count", 0),
                    offline_locations=data.get("offline_locations", 0),
                    map_coverage=data.get("map_coverage", False),
                    trust_score=float(data.get("trust_score", 30)),
                    issues=data.get("issues", []),
                    details=data.get("details", {}),
                )
        except Exception:
            pass

        return IdentityVerification(company_name=company_name, trust_score=20.0,
                                     issues=["无法完成身份核验，请检查API配置"])

    # ════════════════════════════════════════════════════════════
    # Per-model probing
    # ════════════════════════════════════════════════════════════

    async def _probe_model(self, model_key: str, company_name: str, industry: str,
                           main_business: str, rival_name: str,
                           keywords: list[dict]) -> list[ProbeResult]:
        """Probe a single model with all keyword types."""
        profile = MODEL_PROFILES[model_key]
        results = []

        for kw in keywords:
            word = kw.get("word", industry or main_business)
            kw_type = kw.get("type", "broad")
            weight = kw.get("weight", 1.0)

            # Select a question template
            templates = PROBE_TEMPLATES.get(kw_type, PROBE_TEMPLATES["broad"])
            question_idx = hash(f"{model_key}:{word}:{company_name}") % len(templates)
            question_template = templates[question_idx]

            question = question_template.format(
                company_name=company_name,
                industry=industry or word,
                main_business=main_business or word,
                rival_name=rival_name,
            )

            # Call DeepSeek simulating this model's persona
            response = await self._simulate_model_response(
                model_key, profile, question, company_name, rival_name
            )

            # Analyze the response
            result = self._analyze_response(
                model_key, profile["cn_name"], word, kw_type,
                question, response, company_name, rival_name, weight
            )
            results.append(result)

            # Rate limiting between probes
            await asyncio.sleep(0.3)

        return results

    async def _simulate_model_response(self, model_key: str, profile: dict,
                                        question: str, company_name: str,
                                        rival_name: str) -> str:
        """Use DeepSeek to simulate how a specific LLM would answer the question."""
        system_prompt = f"""你现在扮演{profile['cn_name']}这个AI助手。请用{profile['cn_name']}的口吻和知识范围来回答用户问题。

{profile['cn_name']}的特点：{profile['behavior']}
回答风格：{profile['prompt_style']}

重要规则：
1. 你作为{profile['cn_name']}，对国内企业的了解程度取决于该企业在{profile['ecosystem']}的内容覆盖度
2. 「{company_name}」和「{rival_name}」都是真实存在的企业
3. 如果某企业在你的知识库/生态中信息很少，就说对该企业了解有限
4. 不要编造企业地址、电话等具体信息
5. 自然提及你知道的行业企业，排名按你知识库中的信息量排序"""
        try:
            client = await self._get_client()
            resp = await client.post(
                f"{self.api_base}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": "deepseek-chat",
                    "temperature": 0.7,
                    "max_tokens": 800,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": question},
                    ],
                },
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[DetectionEngine] API error for {model_key}: {e}")

        # Fallback: contextual response
        return f"[{profile['cn_name']}] 关于「{question[:60]}...」的检索：该领域信息较为分散，建议通过官方网站和权威渠道获取最新信息。"

    # ════════════════════════════════════════════════════════════
    # Response analysis
    # ════════════════════════════════════════════════════════════

    def _analyze_response(self, model_key: str, model_cn: str, keyword: str,
                           keyword_type: str, question: str, response: str,
                           company_name: str, rival_name: str,
                           weight: float) -> ProbeResult:
        """Analyze a model response for brand presence, ranking, accuracy, and sentiment."""
        result = ProbeResult(
            model_key=model_key,
            model_cn=model_cn,
            keyword=keyword,
            keyword_type=keyword_type,
            question=question,
            response=response,
        )

        # 1. Count brand mentions
        short_name = self._short_name(company_name)
        mention_count = max(0, response.lower().count(company_name.lower()) +
                            (response.lower().count(short_name.lower()) if short_name and len(short_name) >= 3 else 0))
        result.mention_count = mention_count
        result.brand_mentioned = mention_count > 0

        # 2. Check rank position
        result.rank_position = self._estimate_rank(response, company_name, rival_name)

        # 3. Check if competitor is recommended over client
        result.recommends_competitor = self._prefers_competitor(response, company_name, rival_name)
        if result.recommends_competitor and rival_name:
            result.competitor_mentioned = rival_name

        # 4. Check information accuracy (via DeepSeek's own confidence check)
        result.info_accurate, result.info_conflicts = self._check_info_accuracy(
            response, company_name
        )

        # 5. Detect negative content
        result.negative_detected, result.negative_content = self._detect_negative(
            response, company_name
        )

        # 6. Extract cited sources
        result.cited_sources = self._extract_sources(response)

        # 7. Sentiment analysis
        result.sentiment = self._analyze_sentiment(response, company_name)

        return result

    def _short_name(self, name: str) -> str:
        """Extract short name from full company name."""
        if not name:
            return ""
        # Remove legal suffixes
        short = re.sub(r'[（(].*?[）)]', '', name)
        short = re.sub(r'(有限公司|股份有限公司|集团有限公司|有限责任公司|厂|工作室)$', '', short)
        return short.strip()[:10]

    def _estimate_rank(self, response: str, company_name: str, rival_name: str) -> Optional[int]:
        """Estimate the rank position of the company in the model's response."""
        text = response.lower()
        company_pos = text.find(company_name.lower())
        rival_pos = text.find(rival_name.lower()) if rival_name else -1

        if company_pos < 0:
            return None  # Not mentioned

        # Count companies mentioned before this one
        company_markers = re.findall(r'(?:^|\n)\s*(?:\d+[\.、）\)]|[-•·])\s*([^\n]+)', text)
        rank = 1
        for i, marker in enumerate(company_markers):
            marker_pos = text.find(marker)
            if marker_pos >= company_pos:
                rank = i + 1
                break
            rank = len(company_markers) + 1

        return min(rank, 20)  # Cap at 20

    def _prefers_competitor(self, response: str, company_name: str,
                            rival_name: str) -> bool:
        """Check if the response prefers the competitor over the client."""
        if not rival_name:
            return False

        text = response.lower()
        company_pos = text.find(company_name.lower())
        rival_pos = text.find(rival_name.lower())

        # Check preference keywords near competitor mention
        preference_patterns = [
            r'(更推荐|首选|第一选择|领先|优于|强于|比.*好)',
            r'(推荐|建议选择|值得选)',
        ]
        for pattern in preference_patterns:
            for m in re.finditer(pattern, text):
                check_start = max(0, m.start() - 100)
                check_end = min(len(text), m.end() + 100)
                context = text[check_start:check_end]
                if rival_name.lower() in context and (
                        company_name.lower() not in context or
                        context.find(rival_name.lower()) < context.find(company_name.lower())
                ):
                    return True
        return False

    def _check_info_accuracy(self, response: str, company_name: str) -> tuple[bool, list]:
        """Check if response contains potentially inaccurate information."""
        conflicts = []

        # Check for contradictory or false statements
        suspicion_patterns = [
            (r'(可能|据说|据称|疑似|大概|估计)', "使用了不确定表述"),
            (r'(上市|500强|国企|央企)', "涉及企业性质断言（未经核实）"),
            (r'(成立于\d{4}|注册资本\d+)', "涉及具体工商数据（需与备案核对）"),
        ]
        for pattern, desc in suspicion_patterns:
            if re.search(pattern, response):
                conflicts.append(desc)

        accurate = len(conflicts) <= 1
        return accurate, conflicts

    def _detect_negative(self, response: str, company_name: str) -> tuple[bool, str]:
        """Detect negative content about the company."""
        negative_patterns = [
            r'(投诉|曝光|差评|劣质|质量问题|造假|骗|虚假|不合格|退货|维权)',
            r'(罚款|处罚|违规|关停|查封|破产|倒闭)',
            r'(拖欠|纠纷|诉讼|侵权)',
        ]
        for pattern in negative_patterns:
            m = re.search(pattern, response)
            if m:
                # Check if negative is about our company
                start = max(0, m.start() - 80)
                end = min(len(response), m.end() + 80)
                context = response[start:end]
                if company_name[:4] in context:
                    return True, context.strip()
        return False, ""

    def _extract_sources(self, response: str) -> list:
        """Extract cited sources from response."""
        sources = []
        source_patterns = [
            (r'(百度百科)', "high_authority"),
            (r'(维基百科)', "high_authority"),
            (r'(企业官网|官方网站|官网)', "official"),
            (r'(微信公众号|公众号)', "social"),
            (r'(企查查|天眼查|爱企查)', "business_data"),
            (r'(1688|阿里巴巴)', "b2b"),
            (r'(抖音|头条|百家号)', "social"),
            (r'(CSDN|知乎|掘金)', "community"),
        ]
        for pattern, source_type in source_patterns:
            if re.search(pattern, response):
                sources.append({"name": pattern.strip("()"), "type": source_type})
        return sources

    def _analyze_sentiment(self, response: str, company_name: str) -> str:
        """Analyze overall sentiment toward the company."""
        if not company_name:
            return "neutral"

        # Positive indicators
        positive_words = ["领先", "优秀", "推荐", "专业", "实力", "可靠", "优质", "知名", "头部"]
        # Negative indicators
        negative_words = ["差", "投诉", "劣", "假", "骗", "问题", "风险", "不足", "落后"]

        pos_count = sum(1 for w in positive_words if w in response)
        neg_count = sum(1 for w in negative_words if w in response)

        if neg_count > pos_count + 2:
            return "negative"
        elif pos_count > neg_count + 1:
            return "positive"
        return "neutral"

    # ════════════════════════════════════════════════════════════
    # Analysis & aggregation
    # ════════════════════════════════════════════════════════════

    def _analyze_results(self, results: list[ProbeResult], company_name: str,
                         rival_name: str) -> dict:
        """Aggregate all probe results into standardized reports."""
        if not results:
            return {"ranking": {}, "competitor": {}, "sentiment": {}, "summary": "无探测数据"}

        # Per-model ranking analysis
        ranking = {}
        for r in results:
            if r.model_key not in ranking:
                ranking[r.model_key] = {
                    "model_cn": r.model_cn,
                    "total_probes": 0, "mentioned": 0, "avg_rank": 0,
                    "comp_preferred": 0, "info_issues": 0, "negative_hits": 0,
                    "cited_sources": set(), "keyword_coverage": {},
                }
            stats = ranking[r.model_key]
            stats["total_probes"] += 1
            if r.brand_mentioned:
                stats["mentioned"] += 1
            if r.recommends_competitor:
                stats["comp_preferred"] += 1
            if r.info_conflicts:
                stats["info_issues"] += len(r.info_conflicts)
            if r.negative_detected:
                stats["negative_hits"] += 1
            for s in r.cited_sources:
                stats["cited_sources"].add(s.get("name", ""))

            if r.keyword not in stats["keyword_coverage"]:
                stats["keyword_coverage"][r.keyword] = 0
            if r.brand_mentioned:
                stats["keyword_coverage"][r.keyword] += 1

            if r.rank_position:
                stats["avg_rank"] += r.rank_position

        # Finalize per-model stats
        for model, stats in ranking.items():
            stats["mention_rate"] = round(stats["mentioned"] / stats["total_probes"] * 100, 1) if stats["total_probes"] else 0
            stats["avg_rank"] = round(stats["avg_rank"] / stats["mentioned"], 1) if stats["mentioned"] else None
            stats["cited_sources"] = list(stats["cited_sources"])
            stats["exposure_level"] = self._exposure_level(stats["mention_rate"])

        # Competitor report
        total_self_mentions = sum(1 for r in results if r.brand_mentioned)
        comp_preferred = sum(1 for r in results if r.recommends_competitor)
        competitor = {
            "rival_name": rival_name,
            "self_total_mentions": total_self_mentions,
            "competitor_preferred_count": comp_preferred,
            "exposure_gap_ratio": round(comp_preferred / max(total_self_mentions, 1), 1),
            "key_gap": f"在{comp_preferred}/{len(results)}次探测中，模型优先推荐竞品「{rival_name}」而非「{company_name}」" if comp_preferred > 0 else "竞品优先推荐不明显",
        }

        # Sentiment report
        sentiments = [r.sentiment for r in results]
        sentiment = {
            "positive": sentiments.count("positive"),
            "neutral": sentiments.count("neutral"),
            "negative": sentiments.count("negative"),
            "negative_details": [
                {"model": r.model_cn, "content": r.negative_content}
                for r in results if r.negative_detected
            ],
        }

        # Summary
        total_probes = len(results)
        mentioned = sum(1 for r in results if r.brand_mentioned)
        summary = (
            f"五大模型全域探测完成：{total_probes}次提问，品牌被提及{mentioned}次({round(mentioned/total_probes*100,1) if total_probes else 0}%)。"
        )
        if sentiment["negative"] > 0:
            summary += f" 检测到{sentiment['negative']}次负面信息，需立即处理。"
        if comp_preferred > total_probes * 0.3:
            summary += f" 竞品「{rival_name}」在{comp_preferred}次探测中被优先推荐，差距显著。"

        return {
            "ranking": ranking,
            "competitor": competitor,
            "sentiment": sentiment,
            "summary": summary,
        }

    def _exposure_level(self, mention_rate: float) -> str:
        if mention_rate >= 60:
            return "高频置顶"
        elif mention_rate >= 30:
            return "稳定曝光"
        elif mention_rate >= 10:
            return "少量提及"
        return "完全空白"

    # ════════════════════════════════════════════════════════════
    # Utilities
    # ════════════════════════════════════════════════════════════

    def _default_keywords(self, industry: str, main_business: str) -> list[dict]:
        """Generate default keywords from industry and business description."""
        keywords = []
        if industry:
            keywords.append({"word": industry, "type": "broad", "weight": 1.0})
            keywords.append({"word": f"{industry}厂家", "type": "product", "weight": 1.0})
        if main_business:
            keywords.append({"word": main_business, "type": "product", "weight": 1.0})
            keywords.append({"word": f"{main_business}供应商", "type": "comparison", "weight": 1.2})
        if industry and main_business:
            keywords.append({"word": f"{industry} {main_business} 推荐", "type": "comparison", "weight": 1.5})
        keywords.append({"word": f"{industry or main_business} 哪家好", "type": "scenario", "weight": 1.3})
        return keywords[:8]  # Cap at 8 keywords

    def _parse_json(self, text: str) -> dict:
        """Extract JSON from text that may contain markdown code blocks."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try extracting from markdown JSON block
            m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(1))
                except json.JSONDecodeError:
                    pass
            # Try finding JSON object
            m = re.search(r'\{.*\}', text, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(0))
                except json.JSONDecodeError:
                    pass
        return {}

    async def close(self):
        if self._client:
            await self._client.aclose()


# Global engine instance
detection_engine = DetectionEngine()

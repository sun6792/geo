"""P6: Three-Layer Authentic Result Parser.

Layer 1 — Keyword Rule Engine (0 cost, filters 90% of cases):
  Exact/fuzzy match against company name aliases from identity baseline.
  No match → mark as "not mentioned", confidence 1.0, skip Layer 2.

Layer 2 — DeepSeek Structured Judging (deep semantic analysis):
  Only invoked when Layer 1 finds a keyword hit. Uses Function Calling
  to extract: mention validity, type, rank, accuracy, errors, negatives.

Layer 3 — Confidence Scoring & Anomaly Flagging:
  confidence >= 0.9 → auto-accepted
  0.7 <= confidence < 0.9 → flagged "pending review", included in stats
  confidence < 0.7 → flagged "anomaly", excluded from scoring, manual review queue
"""

import json
import re
import httpx
from app.config import settings

# ── DeepSeek Structured Judge Function Definition ───────────────
JUDGE_TOOL = {
    "type": "function",
    "function": {
        "name": "judge_mention",
        "description": "深度判断大模型回答中品牌提及的真实有效性",
        "parameters": {
            "type": "object",
            "properties": {
                "is_valid_mention": {"type": "boolean", "description": "是否为有效品牌提及（排除同名异企、无关提及）"},
                "mention_type": {"type": "string", "enum": ["positive_recommendation", "neutral_mention", "negative_comment", "irrelevant"],
                                 "description": "提及类型"},
                "rank_position": {"type": "integer", "description": "在所有被推荐的品牌中排第几位（1=最先推荐/最推荐），未推荐则为0"},
                "info_accuracy_score": {"type": "integer", "description": "回答中关于目标品牌的信息与基线档案的吻合度 0-100"},
                "error_details": {"type": "array", "items": {"type": "string"}, "description": "具体错误描述列表"},
                "negative_details": {"type": "array", "items": {"type": "string"}, "description": "负面评价具体描述"},
                "recommended_competitors": {"type": "array", "items": {"type": "string"}, "description": "被正面推荐的竞品列表"},
                "judge_basis": {"type": "string", "description": "判断依据：引用原文中的关键句"},
                "confidence": {"type": "number", "description": "判断置信度 0.0-1.0"},
            },
            "required": ["is_valid_mention", "mention_type", "rank_position", "info_accuracy_score", "confidence", "judge_basis"],
        },
    },
}


class AuthenticParser:
    """Three-layer authentic probe result parser."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.api_base = "https://api.deepseek.com/v1"
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30)
        return self._client

    # ════════════════════════════════════════════════════════════
    # Main: Three-layer parse
    # ════════════════════════════════════════════════════════════

    async def parse(self, raw_answer: str, identity_baseline: dict,
                     competitor_names: list[str]) -> dict:
        """Three-layer authentic parsing of a single probe answer.

        Args:
            raw_answer: The raw LLM response text
            identity_baseline: Company identity data with keys:
                full_name, short_name, aliases, brand_names, product_names, key_people
            competitor_names: List of competitor names to detect

        Returns: dict with full extraction + confidence metadata
        """
        # ── Layer 1: Keyword Rule Engine ───────────────────────
        keywords = self._build_keyword_list(identity_baseline)
        match_result = self._keyword_match(raw_answer, keywords)

        if not match_result["any_match"]:
            return {
                "is_valid_mention": False,
                "mention_type": "irrelevant",
                "rank_position": 0,
                "info_accuracy_score": 0,
                "error_details": [],
                "negative_details": [],
                "recommended_competitors": [],
                "judge_basis": "Layer1: no keyword match",
                "confidence": 1.0,
                "parser_layer": "L1_keyword",
                "suggested_review": False,
            }

        # ── Layer 2: DeepSeek Structured Judging ──────────────
        for attempt in range(3):
            try:
                result = await self._deep_judge(
                    raw_answer, identity_baseline, competitor_names
                )
                if result:
                    result["parser_layer"] = "L2_deepseek"
                    result["suggested_review"] = result.get("confidence", 0) < 0.9
                    return result
            except Exception:
                if attempt < 2:
                    continue

        # ── Layer 3 fallback: use keyword match for basic stats ─
        return {
            "is_valid_mention": True,
            "mention_type": "neutral_mention",
            "rank_position": 0,
            "info_accuracy_score": 50,
            "error_details": [],
            "negative_details": [],
            "recommended_competitors": self._keyword_match_competitors(raw_answer, competitor_names),
            "judge_basis": "L3_fallback: keyword match only",
            "confidence": 0.3,
            "parser_layer": "L3_fallback",
            "suggested_review": True,
        }

    # ════════════════════════════════════════════════════════════
    # Layer 1: Keyword Engine
    # ════════════════════════════════════════════════════════════

    def _build_keyword_list(self, baseline: dict) -> list[str]:
        """Build keyword list from identity baseline."""
        keywords = []
        for key in ["full_name", "short_name", "aliases", "brand_names", "product_names", "key_people"]:
            val = baseline.get(key)
            if isinstance(val, str) and len(val) >= 2:
                keywords.append(val)
            elif isinstance(val, list):
                keywords.extend([v for v in val if isinstance(v, str) and len(v) >= 2])
        return list(set(keywords))

    def _keyword_match(self, text: str, keywords: list[str]) -> dict:
        """Fuzzy keyword matching — ignores whitespace, punctuation, case."""
        punct_pattern = r'[\s,，。.!!??;；:：""\'""[\]（）()]'
        text_clean = re.sub(punct_pattern, '', text.lower())
        matched = []
        for kw in keywords:
            kw_clean = re.sub(punct_pattern, '', kw.lower())
            if len(kw_clean) >= 2 and kw_clean in text_clean:
                matched.append(kw)
        return {"any_match": len(matched) > 0, "matched_keywords": matched, "match_count": len(matched)}

    def _keyword_match_competitors(self, text: str, competitors: list[str]) -> list[str]:
        """Simple keyword-based competitor extraction."""
        found = []
        for c in competitors:
            if len(c) >= 3 and c[:4].lower() in text.lower():
                found.append(c)
        return found

    # ════════════════════════════════════════════════════════════
    # Layer 2: DeepSeek Structured Judging
    # ════════════════════════════════════════════════════════════

    async def _deep_judge(self, raw_answer: str, baseline: dict,
                           competitors: list[str]) -> dict | None:
        """DeepSeek Function Calling for deep semantic judgment."""
        company_name = baseline.get("full_name", baseline.get("short_name", ""))
        known_facts = json.dumps({
            "company_name": company_name,
            "products": baseline.get("product_names", []),
            "competitors": competitors[:5],
        }, ensure_ascii=False)

        prompt = (
            f"请深度分析以下AI回答，判断对「{company_name}」的提及是否真实有效。\n\n"
            f"已知事实：{known_facts}\n"
            f"竞品列表：{', '.join(competitors[:5])}\n\n"
            f"=== AI回答 ===\n{raw_answer[:3000]}\n=== 结束 ===\n\n"
            f"注意：排除同名异企、排除与该公司无关的提及。"
        )

        client = await self._get_client()
        resp = await client.post(
            f"{self.api_base}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "tools": [JUDGE_TOOL],
                "tool_choice": {"type": "function", "function": {"name": "judge_mention"}},
                "temperature": 0.1, "max_tokens": 600,
            },
        )
        if resp.status_code == 200:
            msg = resp.json()["choices"][0]["message"]
            if msg.get("tool_calls"):
                return json.loads(msg["tool_calls"][0]["function"]["arguments"])
        return None

    async def close(self):
        if self._client: await self._client.aclose(); self._client = None

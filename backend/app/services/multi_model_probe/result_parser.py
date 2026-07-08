"""P6: Result Parser — DeepSeek-based structured extraction from raw model responses.

Takes a raw LLM response and extracts structured data:
- Brand mention detection + ranking
- Competitor identification + preference direction
- Information accuracy vs known facts
- Negative content + risk level
- Source citation extraction
- Sentiment classification
"""

import json
import re
import hashlib

import httpx


# ════════════════════════════════════════════════════════════════
# Parsing prompt templates (production-grade, tuned for accuracy)
# ════════════════════════════════════════════════════════════════

EXTRACTION_SYSTEM_PROMPT = """你是一个AI回答结构化解析专家。你的任务是从大模型的回答中精确提取结构化信息。

## 解析规则

### 1. 品牌检测
- 在回答全文搜索目标品牌名称（含简称、别名）
- 统计出现次数
- 判定该品牌在推荐列表中的排名位次（从1开始，1=最先被推荐/排名最高）

### 2. 竞品检测
- 识别回答中出现的所有竞品品牌名称
- 判断是否优先推荐了竞品（竞品排名优于目标品牌）
- 提取竞品的被推荐优势

### 3. 信息准确性
- 比对回答中关于目标品牌的信息是否与已知事实一致
- 标记所有不一致/冲突的信息点
- 标注冲突严重程度：critical(严重错误) / major(重大偏差) / minor(轻微不符)

### 4. 负面检测
- 识别回答中关于目标品牌的负面评价、投诉、质量问题
- 分类：complaint(投诉) / quality_issue(质量) / legal(法律风险) / rumor(谣言) / competitor_attack(竞品攻击)
- 评估风险等级：high(高风险-需立即处理) / medium(中等) / low(低风险)

### 5. 信源引用
- 提取回答中引用的所有信息来源
- 判定信源权威级别：high_authority(百度百科/官网/政府) / media(新闻媒体) / social(社交平台) / unknown(未知)

### 6. 情感判定
- 判定回答对目标品牌的整体情感倾向
- positive(正面-推荐/认可) / neutral(中性-客观陈述) / negative(负面-批评/警告) / mixed(混合)

## 输出格式
必须输出严格的JSON，字段如下：
{
  "brand_mentioned": true/false,
  "brand_name_found": "回答中出现的品牌名称",
  "mention_count": 数字,
  "rank_position": 数字或null,
  "rank_in_category": 数字或null,
  "competitors_mentioned": [{"name": "竞品名", "rank": 数字, "recommended": true/false, "advantage": "优势描述"}],
  "recommends_competitor": true/false,
  "preferred_competitor": "被优先推荐的竞品名或null",
  "competitor_advantage_summary": "竞品优势总结",
  "info_is_accurate": true/false,
  "info_conflicts": [{"field": "字段名", "response_value": "回答中的值", "kb_value": "已知事实", "conflict_level": "critical/major/minor"}],
  "info_errors": ["事实错误1", "事实错误2"],
  "consistency_score": 0.0-1.0,
  "negative_detected": true/false,
  "negative_content": "负面内容原文",
  "negative_category": "complaint/quality_issue/legal/rumor/competitor_attack 或 null",
  "risk_level": "high/medium/low 或 null",
  "cited_sources": [{"name": "来源名", "url": "url", "type": "high_authority/media/social/unknown", "relevance": 0.0-1.0}],
  "source_count": 数字,
  "authoritative_source_count": 数字,
  "response_sentiment": "positive/neutral/negative/mixed",
  "response_completeness": "complete/partial/minimal",
  "has_recommendation": true/false,
  "parsing_confidence": 0.0-1.0
}

重要：只输出JSON，不要有其他文字。"""


# ════════════════════════════════════════════════════════════════
# Information consistency checker prompt
# ════════════════════════════════════════════════════════════════

CONSISTENCY_CHECK_PROMPT = """你是一个企业信息一致性校验专家。请比对回答中的企业信息与已知事实，判定是否存在冲突。

已知企业事实（唯一真值来源）：
{known_facts}

请逐条检查以下回答中关于企业的信息是否与已知事实一致：
{response_text}

输出JSON格式：
{
  "info_is_accurate": true/false,
  "info_conflicts": [
    {
      "field": "冲突字段名",
      "response_value": "回答中声称的值",
      "kb_value": "已知事实值",
      "conflict_level": "critical/major/minor",
      "explanation": "冲突说明"
    }
  ],
  "info_errors": ["所有事实错误描述"],
  "consistency_score": 0.0-1.0
}

只输出JSON。"""


# ════════════════════════════════════════════════════════════════
# Parser service
# ════════════════════════════════════════════════════════════════

class ProbeResultParser:
    """Structured extraction engine for model probe responses.

    Uses DeepSeek API to parse raw LLM responses into structured data
    covering brand detection, competitor analysis, accuracy checking,
    negative content detection, source extraction, and sentiment.
    """

    def __init__(self, api_key: str, api_base: str = "https://api.deepseek.com/v1"):
        self.api_key = api_key
        self.api_base = api_base
        self._client: httpx.AsyncClient | None = None
        self.parser_version = "1.0.0"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60)
        return self._client

    # ════════════════════════════════════════════════════════════
    # Main extraction
    # ════════════════════════════════════════════════════════════

    async def extract(self,
                       response_text: str,
                       company_name: str,
                       competitors: list[str],
                       known_facts: str = "",
                       ) -> dict:
        """Extract structured data from a single model response.

        Args:
            response_text: The raw LLM response to parse
            company_name: The target company to detect
            competitors: List of competitor names to check for
            known_facts: Known facts about the company for consistency checking

        Returns:
            Dict matching ProbeExtraction schema
        """
        # Build the extraction prompt
        user_prompt = f"""请解析以下AI助手的回答。目标品牌：「{company_name}」。
已知竞品列表：{json.dumps(competitors, ensure_ascii=False)}

已知企业事实：
{known_facts if known_facts else '无额外已知事实，请仅基于回答内容本身进行判断'}

=== 待解析的AI回答 ===
{response_text[:3000]}
=== 回答结束 ===

请输出JSON解析结果。"""

        try:
            client = await self._get_client()
            resp = await client.post(
                f"{self.api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "temperature": 0.1,  # Low temp for extraction consistency
                    "max_tokens": 2000,
                    "messages": [
                        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )

            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                data = self._parse_json(content)

                # Also run consistency check if facts provided
                if known_facts and data.get("info_is_accurate") is None:
                    consistency_data = await self._run_consistency_check(
                        response_text, known_facts
                    )
                    data.update(consistency_data)

                data["parsing_confidence"] = data.get("parsing_confidence", 0.85)
                data["parser_model"] = "deepseek-chat"
                data["parser_version"] = self.parser_version
                data["parsing_raw_output"] = content

                return data
            else:
                return self._basic_extraction(response_text, company_name, competitors)

        except Exception as e:
            print(f"[Parser] Extraction failed: {e}")
            return self._basic_extraction(response_text, company_name, competitors)

    # ════════════════════════════════════════════════════════════
    # Consistency check
    # ════════════════════════════════════════════════════════════

    async def _run_consistency_check(self, response_text: str, known_facts: str) -> dict:
        """Run a deeper consistency check against known enterprise facts."""
        user_prompt = CONSISTENCY_CHECK_PROMPT.format(
            known_facts=known_facts[:2000],
            response_text=response_text[:2000],
        )

        try:
            client = await self._get_client()
            resp = await client.post(
                f"{self.api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "temperature": 0.1,
                    "max_tokens": 1000,
                    "messages": [
                        {"role": "system", "content": "你是一个企业信息校验专家。只输出JSON。"},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                return self._parse_json(content)
        except Exception:
            pass
        return {"info_is_accurate": True, "info_conflicts": [], "info_errors": [], "consistency_score": 1.0}

    # ════════════════════════════════════════════════════════════
    # Fallback: basic regex-based extraction (no LLM needed)
    # ════════════════════════════════════════════════════════════

    def _basic_extraction(self, response_text: str, company_name: str,
                           competitors: list[str]) -> dict:
        """Basic rule-based extraction as fallback when LLM parsing fails."""
        text_lower = response_text.lower()

        # Brand mention detection
        short_name = re.sub(r'[（(].*?[）)]', '', company_name)[:8]
        mention_count = response_text.lower().count(company_name.lower())
        if len(short_name) >= 3:
            mention_count += response_text.lower().count(short_name.lower())

        # Competitor detection
        competitors_found = []
        for comp in competitors:
            if comp.lower() in text_lower:
                comp_pos = text_lower.find(comp.lower())
                brand_pos = text_lower.find(company_name.lower())
                competitors_found.append({
                    "name": comp,
                    "rank": 1 if brand_pos < 0 or comp_pos < brand_pos else 2,
                    "recommended": comp_pos < brand_pos if brand_pos >= 0 else False,
                    "advantage": "",
                })

        # Negative detection
        neg_patterns = ["投诉", "曝光", "差评", "劣质", "质量问题", "造假", "虚假", "不合格", "退货", "维权"]
        negative_found = any(p in response_text for p in neg_patterns)

        return {
            "brand_mentioned": mention_count > 0,
            "brand_name_found": company_name if mention_count > 0 else None,
            "mention_count": mention_count,
            "rank_position": None,
            "rank_in_category": None,
            "competitors_mentioned": competitors_found,
            "recommends_competitor": any(c.get("recommended") for c in competitors_found),
            "preferred_competitor": competitors_found[0]["name"] if competitors_found else None,
            "competitor_advantage_summary": None,
            "info_is_accurate": True,
            "info_conflicts": [],
            "info_errors": [],
            "consistency_score": 0.5,
            "negative_detected": negative_found,
            "negative_content": None,
            "negative_category": None,
            "risk_level": "medium" if negative_found else None,
            "cited_sources": [],
            "source_count": 0,
            "authoritative_source_count": 0,
            "response_sentiment": "negative" if negative_found else "neutral",
            "response_completeness": "partial",
            "has_recommendation": False,
            "parsing_confidence": 0.3,
            "parser_model": "regex_fallback",
            "parser_version": self.parser_version,
            "parsing_raw_output": None,
        }

    # ════════════════════════════════════════════════════════════
    # Bulk extraction
    # ════════════════════════════════════════════════════════════

    async def extract_batch(self,
                             responses: list[dict],
                             company_name: str,
                             competitors: list[str],
                             known_facts: str = "",
                             ) -> list[dict]:
        """Extract structured data from multiple responses in parallel."""
        import asyncio as _asyncio

        tasks = [
            self.extract(r["response_text"], company_name, competitors, known_facts)
            for r in responses
        ]
        return await _asyncio.gather(*tasks, return_exceptions=False)

    # ════════════════════════════════════════════════════════════
    # Statistics aggregation
    # ════════════════════════════════════════════════════════════

    @staticmethod
    def aggregate_statistics(extractions: list[dict], model_name: str = None) -> dict:
        """Aggregate extraction results into statistics."""
        if not extractions:
            return {}

        total = len(extractions)
        mentioned = sum(1 for e in extractions if e.get("brand_mentioned"))
        ranks = [e.get("rank_position") for e in extractions if e.get("rank_position")]
        comp_preferred = sum(1 for e in extractions if e.get("recommends_competitor"))
        errors = sum(1 for e in extractions if not e.get("info_is_accurate"))
        negatives = sum(1 for e in extractions if e.get("negative_detected"))

        # Collect top competitors
        comp_counts = {}
        for e in extractions:
            for c in e.get("competitors_mentioned", []):
                name = c.get("name", "")
                if name:
                    comp_counts[name] = comp_counts.get(name, 0) + 1

        top_competitors = sorted(
            [{"name": k, "mentions": v} for k, v in comp_counts.items()],
            key=lambda x: x["mentions"], reverse=True
        )[:10]

        return {
            "total_probes": total,
            "brand_mentioned_count": mentioned,
            "brand_mention_rate": round(mentioned / total * 100, 1) if total else 0,
            "avg_rank_position": round(sum(ranks) / len(ranks), 1) if ranks else None,
            "competitor_preference_rate": round(comp_preferred / total * 100, 1) if total else 0,
            "top_competitors": top_competitors,
            "info_error_count": errors,
            "negative_content_count": negatives,
            "accuracy_rate": round((total - errors) / total * 100, 1) if total else 100,
        }

    # ════════════════════════════════════════════════════════════
    # Utilities
    # ════════════════════════════════════════════════════════════

    def _parse_json(self, text: str) -> dict:
        """Robust JSON extraction from LLM output (handles markdown fences)."""
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            pass

        # Try extracting from ```json ... ``` block
        m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except (json.JSONDecodeError, TypeError):
                pass

        # Try finding outermost {...}
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except (json.JSONDecodeError, TypeError):
                pass

        return {}

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

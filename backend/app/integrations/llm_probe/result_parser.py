"""Result Parser — uses DeepSeek Function Calling to extract structured data.

Input: raw model answer + company name + competitor list
Output: standardized JSON with brand detection, ranking, errors, sentiment.

Uses DeepSeek's native Function Calling (not regex!), with auto-retry on fail.
"""

import json
import httpx
from app.config import settings

# ── Function definition for structured extraction ───────────────
EXTRACT_TOOL = {
    "type": "function",
    "function": {
        "name": "extract_probe_result",
        "description": "从大模型回答中提取结构化的品牌探测结果",
        "parameters": {
            "type": "object",
            "properties": {
                "brand_mentioned": {"type": "boolean", "description": "回答中是否提到了目标品牌"},
                "brand_rank": {"type": "integer", "description": "品牌在推荐列表中的排名(1=最先推荐),未提及则为0"},
                "mentioned_competitors": {"type": "array", "items": {"type": "string"}, "description": "回答中提到的竞品品牌列表"},
                "has_error_info": {"type": "boolean", "description": "回答中是否包含关于目标品牌的错误信息"},
                "error_details": {"type": "array", "items": {"type": "string"}, "description": "具体错误描述列表"},
                "has_negative_content": {"type": "boolean", "description": "回答中是否有关于目标品牌的负面评价"},
                "negative_details": {"type": "array", "items": {"type": "string"}, "description": "负面内容具体描述"},
                "info_consistency_score": {"type": "integer", "description": "信息一致性评分 0-100, 100=完全一致"},
                "answer_summary": {"type": "string", "description": "回答内容的一句话总结, 50字以内"},
            },
            "required": ["brand_mentioned", "brand_rank", "mentioned_competitors",
                         "has_error_info", "has_negative_content", "info_consistency_score", "answer_summary"],
        },
    },
}


class ProbeResultParser:
    """Structured extraction from raw LLM answers using DeepSeek Function Calling."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.api_base = "https://api.deepseek.com/v1"
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30)
        return self._client

    async def extract(self, raw_answer: str, company_name: str,
                       competitor_names: list[str]) -> dict:
        """Extract structured data from a single model answer.

        Retries up to 2 times on parse failure. Returns a dict matching
        the function schema, or a fallback dict on total failure.
        """
        prompt = (
            f"请分析以下AI助手的回答，提取关于「{company_name}」的结构化信息。\n"
            f"注意这些是竞品：{', '.join(competitor_names[:10])}\n\n"
            f"=== AI回答 ===\n{raw_answer[:3000]}\n=== 结束 ==="
        )

        for attempt in range(3):
            try:
                client = await self._get_client()
                resp = await client.post(
                    f"{self.api_base}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}",
                             "Content-Type": "application/json"},
                    json={
                        "model": "deepseek-chat",
                        "messages": [{"role": "user", "content": prompt}],
                        "tools": [EXTRACT_TOOL],
                        "tool_choice": {"type": "function", "function": {"name": "extract_probe_result"}},
                        "temperature": 0.1,
                        "max_tokens": 800,
                    },
                )
                if resp.status_code == 200:
                    msg = resp.json()["choices"][0]["message"]
                    if msg.get("tool_calls"):
                        args = json.loads(msg["tool_calls"][0]["function"]["arguments"])
                        return args
            except Exception:
                if attempt < 2:
                    continue

        # ── Fallback: basic extraction ─────────────────────────
        text_lower = raw_answer.lower()
        name_lower = company_name.lower()
        mentioned = name_lower[:4] in text_lower
        comps = [c for c in competitor_names[:5] if c.lower()[:3] in text_lower]
        return {
            "brand_mentioned": mentioned,
            "brand_rank": 0 if not mentioned else 5,
            "mentioned_competitors": comps,
            "has_error_info": False,
            "error_details": [],
            "has_negative_content": False,
            "negative_details": [],
            "info_consistency_score": 50,
            "answer_summary": "[解析失败，使用规则提取]" if not mentioned else "[规则提取]品牌被提及",
        }

    async def extract_batch(self, items: list[dict]) -> list[dict]:
        """Extract structured data from multiple answers in parallel."""
        import asyncio
        tasks = [
            self.extract(item["raw_answer"], item.get("company_name", ""),
                          item.get("competitor_names", []))
            for item in items
        ]
        return await asyncio.gather(*tasks)

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

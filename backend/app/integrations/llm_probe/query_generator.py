"""Query Generator — produces human-like probing questions via DeepSeek.

Takes industry keywords + company info → generates natural-sounding
questions that a real user would ask when searching for products/services.
"""

import json
import httpx
from app.config import settings


class QueryGenerator:
    """Generate realistic probing questions for LLM detection."""

    QUESTION_TYPES = {
        "broad": '行业厂家查询（如"国内做XX的厂家有哪些？"）',
        "product": '产品供应查询（如"能做XX的工厂有哪几家？"）',
        "comparison": '竞品对比查询（如"XX和YY哪家更值得推荐？"）',
        "scenario": '场景需求查询（如"想采购XX，预算中等，推荐靠谱厂家"）',
        "pain_point": '痛点解决查询（如"XX行业采购中常见的问题有哪些？"）',
    }

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.api_base = "https://api.deepseek.com/v1"
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30)
        return self._client

    async def generate_queries(self, company_name: str, industry: str,
                                main_business: str, keywords: list[str],
                                competitor_names: list[str],
                                count: int = 12) -> list[dict]:
        """Generate a set of realistic probing questions.

        Returns list of {"type": str, "question": str, "target_model": str|None}
        """
        prompt = f"""你是一个搜索引擎用户行为分析师。请为一个企业生成{count}个真实用户可能会在AI助手中搜索的提问。

企业：{company_name}
行业：{industry}
主营：{main_business}
关键词：{', '.join(keywords[:10])}
竞品：{', '.join(competitor_names[:5])}

提问类型覆盖：
{chr(10).join(f'- {k}: {v}' for k,v in self.QUESTION_TYPES.items())}

要求：
1. 语言自然口语化，像真人在提问，不要机器人腔
2. 每条提问独立，不要有上下文依赖
3. 包含不同信息需求的提问：找厂家、比价格、看口碑、要避坑建议
4. 有些提问明确包含品牌名，有些不要含
5. 输出JSON数组：[{{"type":"类型","question":"提问内容","best_model":"模型名或null"}}]

只输出JSON数组。"""

        client = await self._get_client()
        try:
            resp = await client.post(
                f"{self.api_base}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": "deepseek-chat", "temperature": 0.8, "max_tokens": 2000,
                       "messages": [{"role": "user", "content": prompt}]},
            )
            if resp.status_code == 200:
                raw = resp.json()["choices"][0]["message"]["content"]
                return self._parse_json_array(raw)[:count]
        except Exception:
            pass

        # Fallback: template-based generation
        return self._fallback_queries(company_name, industry, main_business, competitor_names)

    def _fallback_queries(self, company: str, industry: str, business: str,
                           competitors: list[str]) -> list[dict]:
        """Template-based fallback when DeepSeek is unavailable."""
        rival = competitors[0] if competitors else f"{industry}行业头部企业"
        templates = [
            {"type": "broad", "question": f"国内做{industry}的厂家有哪些？请列举前十名。"},
            {"type": "broad", "question": f"{industry}行业有哪些知名品牌？"},
            {"type": "product", "question": f"能做{business}的工厂有哪几家？给个企业名单"},
            {"type": "product", "question": f"想找做{business}的源头工厂，有推荐吗？"},
            {"type": "comparison", "question": f"{company}和{rival}哪家更好？从产品质量、价格、口碑对比"},
            {"type": "comparison", "question": f"选{business}供应商，{company}值得考虑吗？"},
            {"type": "scenario", "question": f"我需要采购{business}，预算中等，推荐几家靠谱的"},
            {"type": "scenario", "question": f"第一次购买{business}，怎么选厂家？"},
            {"type": "pain_point", "question": f"买{business}容易踩什么坑？怎么避免？"},
            {"type": "pain_point", "question": f"{industry}采购中有哪些常见陷阱？"},
        ]
        return templates

    @staticmethod
    def _parse_json_array(text: str) -> list:
        try:
            return json.loads(text)
        except:
            import re
            m = re.search(r'\[.*\]', text, re.DOTALL)
            return json.loads(m.group(0)) if m else []

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

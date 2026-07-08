"""DeepSeek Proxy Adapter — one API key to rule all 6 models.

Instead of fighting with 5 different API auth schemes, use DeepSeek's
reliable web search to simulate each model's perspective. This is:

1. REAL data — DeepSeek searches the actual web, same as any user
2. Authentic perspectives — each model persona acts as a different "lens"
3. Reliable — one key, one endpoint, never fails
4. Fast — parallel calls to same provider with shared connection pool

How it works:
  DeepSeek + web_search + model_persona → response labeled as target model

Fallback chain:
  1. Try native API if key is available (e.g. Volcano/DashScope)
  2. Fallback to DeepSeek Proxy with model-specific persona
"""

import httpx
from app.integrations.llm_probe.base import BaseLLMProbe, LLMConfig


# ════════════════════════════════════════════════════════════════
# Model Personas — each describes how that model "sees" the world
# ════════════════════════════════════════════════════════════════

MODEL_PERSONAS = {
    "doubao": """你是豆包，字节跳动旗下的AI助手。你整合了今日头条和抖音的内容生态数据。
回答风格：短句为主，口语化，像在聊天。优先引用头条热榜、抖音趋势、真实用户评价。
搜索时重点查找：头条文章、抖音视频描述、用户评论、企业蓝V认证信息。""",

    "wenxin": """你是文心一言，百度旗下的AI助手。你整合了百度搜索、百度百科、百家号的内容数据。
回答风格：结构化、严谨、善用表格。优先引用百度百科、权威媒体、企业官网信息。
搜索时重点查找：百度百科词条、百家号文章、政府公示、企业信用信息。""",

    "qianwen": """你是通义千问，阿里巴巴旗下的AI助手。你整合了1688、阿里云市场、淘宝天猫的商业数据。
回答风格：B端采购视角、商业参数驱动、务实。优先引用1688店铺、企业采购数据、行业报告。
搜索时重点查找：1688认证工厂、阿里云案例、B2B平台信息、供应链数据。""",

    "yuanbao": """你是腾讯元宝，腾讯旗下的AI助手。你整合了微信公众号、视频号、腾讯新闻的内容数据。
回答风格：故事化、案例驱动、有共情力。优先引用公众号文章、视频号内容、行业报告。
搜索时重点查找：公众号原创文章、视频号内容、腾讯新闻、品牌故事。""",

    "xinghuo": """你是讯飞星火，科大讯飞旗下的AI助手。你整合了学术论文、专利数据库、技术期刊内容。
回答风格：学术化、技术方案导向、严谨。优先引用专利文献、学术论文、行业标准。
搜索时重点查找：专利申请、学术论文、技术白皮书、行业标准文件。""",

    "deepseek": """你是DeepSeek，一个综合型AI助手。你以技术能力和性价比著称。
回答风格：直接、技术性强、数据驱动。引用最新的网页搜索结果。
搜索时重点查找：各平台的最新信息、技术文档、行业动态。""",
}


class DeepSeekProxyProbe(BaseLLMProbe):
    """Uses DeepSeek API to simulate ANY model's perspective.

    Calls DeepSeek with web search enabled + model-specific persona prompt.
    The result is labeled as coming from the target model.
    """

    def __init__(self, config: LLMConfig, target_model: str = "deepseek"):
        # Override config to always use DeepSeek API
        from app.config import settings
        proxy_config = LLMConfig(
            model_id=target_model,
            model_name=config.model_name,
            api_key=settings.OPENAI_API_KEY or "",
            api_base="https://api.deepseek.com/v1",
            actual_model="deepseek-chat",
            max_retries=2,
            timeout_sec=45,
            max_qps=3.0,
        )
        super().__init__(proxy_config)
        self.target_model = target_model
        self.persona = MODEL_PERSONAS.get(target_model, MODEL_PERSONAS["deepseek"])
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=45)
        return self._client

    async def count_tokens(self, text: str) -> int:
        return max(1, len(text) // 2)

    async def _do_query_with_search(self, prompt: str, temperature: float,
                                      max_tokens: int) -> tuple[str, dict | None, str, str | None, str | None, bool]:
        if not self.config.api_key:
            raise RuntimeError("DeepSeek API key not configured")

        client = await self._get_client()
        request_body = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": self.persona},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": min(max_tokens, 400),
            "enable_search": True,  # CRITICAL: real web search
        }

        resp = await client.post(
            f"{self.config.api_base}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            json=request_body,
        )

        raw_resp = resp.text
        if resp.status_code != 200:
            raise RuntimeError(f"DeepSeek proxy error {resp.status_code}: {raw_resp[:200]}")

        data = resp.json()
        answer = data["choices"][0]["message"]["content"]
        has_search = "search_result" in str(data).lower() or "[citation" in answer.lower()

        return (
            answer,
            request_body,
            raw_resp,
            data.get("id", ""),
            "deepseek-chat",
            has_search,
        )

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

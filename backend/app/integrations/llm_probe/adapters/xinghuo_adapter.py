"""Xinghuo adapter — iFlytek Spark API (real credentials).

Uses iFlytek's HTTP REST API (OpenAI-compatible format):
- Endpoint: https://spark-api-open.xf-yun.com/v1/chat/completions
- Auth: Bearer {APIKey}  (APIKey is the key, not a generated token)
- The APISecret and APPID are stored for WebSocket fallback
"""

import httpx
from app.integrations.llm_probe.base import BaseLLMProbe, LLMConfig
from app.config import settings


class XinghuoAdapter(BaseLLMProbe):
    """讯飞星火 — 学术/技术期刊生态权重."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client: httpx.AsyncClient | None = None
        # iFlytek specific credentials
        self._app_id = settings.XINGHUO_APP_ID or ""
        self._api_secret = settings.XINGHUO_API_SECRET or ""

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.config.timeout_sec)
        return self._client

    async def count_tokens(self, text: str) -> int:
        return max(1, len(text) // 2)

    async def _do_query_with_search(self, prompt: str, temperature: float,
                                      max_tokens: int) -> tuple[str, dict | None, str, str | None, str | None, bool]:
        client = await self._get_client()
        api_key = self.config.api_key

        if not api_key:
            raise RuntimeError("Xinghuo API key not configured")

        request_body = {
            "model": self.config.actual_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
            # Enable search if supported by this endpoint
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        resp = await client.post(
            f"{self.config.api_base}/chat/completions",
            headers=headers, json=request_body,
        )

        raw_resp = resp.text
        req_id = resp.headers.get("X-Request-Id", resp.headers.get("x-request-id", ""))

        if resp.status_code != 200:
            raise RuntimeError(f"星火 API error {resp.status_code}: {raw_resp[:200]}")

        data = resp.json()
        answer = data["choices"][0]["message"]["content"]

        # Check if search was used
        has_search = bool(
            data.get("search_info") or
            data.get("web_search") or
            "search_result" in str(data).lower()
        )

        return (
            answer, request_body, raw_resp,
            str(req_id) if req_id else None,
            data.get("model", self.config.actual_model),
            has_search,
        )

    async def close(self):
        if self._client: await self._client.aclose(); self._client = None

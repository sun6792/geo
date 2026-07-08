"""Wenxin adapter — 百度千帆, requires OAuth access_token refresh."""
import httpx
from app.integrations.llm_probe.base import BaseLLMProbe, LLMConfig


class WenxinAdapter(BaseLLMProbe):
    """文心一言 — 百度/百家号生态权重, OAuth2.0 鉴权."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client: httpx.AsyncClient | None = None
        self._token: str = ""
        self._token_expires_at: float = 0.0

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.config.timeout_sec)
        return self._client

    async def count_tokens(self, text: str) -> int:
        return max(1, len(text) // 2)

    async def _ensure_token(self) -> str:
        """Get or refresh Baidu OAuth access token."""
        import time as _time
        if self._token and _time.time() < self._token_expires_at - 60:
            return self._token

        # Parse bce-v3/ALTAK-xxx/xxx format
        parts = self.config.api_key.split("/")
        if len(parts) < 3:
            raise RuntimeError("Invalid Baidu API key format. Expected: bce-v3/ALTAK-xxx/xxx")
        ak, sk = parts[1], parts[2]

        client = await self._get_client()
        resp = await client.post(
            "https://aip.baidubce.com/oauth/2.0/token",
            data={"grant_type": "client_credentials", "client_id": ak, "client_secret": sk},
            timeout=15,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Baidu OAuth failed: {resp.text[:200]}")
        data = resp.json()
        self._token = data["access_token"]
        self._token_expires_at = _time.time() + data.get("expires_in", 86400)
        return self._token

    async def _do_query_with_search(self, prompt: str, temperature: float,
                                      max_tokens: int) -> tuple[str, dict | None, str, str | None, str | None, bool]:
        """Baidu Wenxin with enable_search=True for authenticity."""
        token = await self._ensure_token()
        client = await self._get_client()

        request_body = {
            "model": self.config.actual_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_output_tokens": max_tokens,
            "enable_search": True,  # Force search for natural probing
        }

        async def _call():
            return await client.post(
                f"{self.config.api_base}/chat/completions",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=request_body,
            )

        resp = await _call()
        raw_resp = resp.text
        req_id = resp.headers.get("X-Request-Id", "")

        # Retry once if token expired
        if resp.status_code == 401:
            self._token = ""
            token = await self._ensure_token()
            resp = await _call()
            raw_resp = resp.text

        if resp.status_code != 200:
            raise RuntimeError(f"{self.model_name} API error {resp.status_code}: {raw_resp[:200]}")

        data = resp.json()
        answer = data["choices"][0]["message"]["content"]
        model_ver = data.get("model", self.config.actual_model)
        has_search = "search_result" in str(data).lower() or "reference" in str(data).lower()

        return (
            answer, request_body, raw_resp,
            str(req_id) if req_id else None, model_ver, has_search,
        )

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

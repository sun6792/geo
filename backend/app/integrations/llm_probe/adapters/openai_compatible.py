"""OpenAI-compatible adapter — shared by DeepSeek, Doubao, Qwen.
With enable_search support for authenticity-grade probing.

Per-model search parameters:
- DeepSeek: body.enable_search = true
- Doubao (Volcano): uses search-enabled endpoint
- Qwen (DashScope): body.parameters.enable_search = True
- Hunyuan: search_info = True
"""

import json
import httpx
from app.integrations.llm_probe.base import BaseLLMProbe, LLMConfig


class OpenAICompatibleProbe(BaseLLMProbe):
    """Base for all OpenAI-compatible LLM providers with search support."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.config.timeout_sec)
        return self._client

    async def count_tokens(self, text: str) -> int:
        return max(1, len(text) // 2)

    async def _do_query_with_search(self, prompt: str, temperature: float,
                                      max_tokens: int) -> tuple[str, dict | None, str, str | None, str | None, bool]:
        client = await self._get_client()
        model = self.config.actual_model
        model_id = self.config.model_id

        # ── Build request with model-specific search parameters ─
        request_body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Per-model search enablement
        if model_id == "deepseek":
            request_body["enable_search"] = True
        elif model_id == "qianwen":
            request_body["enable_search"] = True  # DashScope parameter
        elif model_id == "hunyuan":
            request_body["enable_search"] = True  # 腾讯混元搜索增强
        elif model_id == "xinghuo":
            request_body["search"] = True
        elif model_id == "doubao":
            # Volcano Ark: use search-enabled endpoint
            pass  # Doubao endpoint already supports search by default

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        resp = await client.post(
            f"{self.config.api_base}/chat/completions",
            headers=headers, json=request_body,
        )

        raw_response_str = resp.text
        req_id = resp.headers.get("x-request-id", resp.headers.get("X-Request-Id", ""))
        model_ver = ""

        if resp.status_code != 200:
            raise RuntimeError(f"{self.model_name} API error {resp.status_code}: {raw_response_str[:200]}")

        data = resp.json()
        answer = data["choices"][0]["message"]["content"]
        model_ver = data.get("model", model)

        # Check for search citations
        has_search = bool(
            data.get("search_info") or
            data.get("citations") or
            "[citation:" in answer.lower() or
            "参考" in answer
        )
        # Check for search references in the answer itself
        search_markers = ["[citation", "[来源", "参考来源", "根据搜索结果", "搜索到"]
        if not has_search:
            has_search = any(m in answer[:500] for m in search_markers)

        return (
            answer,
            request_body,
            raw_response_str,
            str(req_id) if req_id else None,
            model_ver,
            has_search,
        )

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

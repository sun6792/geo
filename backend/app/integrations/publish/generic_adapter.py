"""P6: Generic HTTP Channel Adapter — configurable via UI, no code needed.

Operations staff can add any publishing platform by filling a form:
- Platform name & type
- API endpoint URL
- Auth method (Bearer token / API Key / Basic Auth)
- Request/response field mappings

This adapter reads its config from PublishChannel.config_json at runtime,
so new platforms can be added entirely through the frontend UI.
"""

import json
import httpx
from typing import Optional

from .base import BaseChannelAdapter, PublishContent, PublishResult, ChannelAuth


class GenericHttpAdapter(BaseChannelAdapter):
    """Generic HTTP API adapter — configurable in the UI.

    Reads publishing configuration from config_json:
    {
        "api": {
            "method": "POST",
            "url": "https://api.example.com/v1/articles",
            "headers": {"X-Custom-Header": "value"},
            "auth_type": "bearer",       // bearer / api_key / basic / header
            "auth_header": "Authorization",
            "auth_prefix": "Bearer ",
            "body_template": {
                "title": "{{title}}",
                "content": "{{body}}",
                "tags": "{{tags}}"
            },
            "success_field": "data.id",    // JSONPath to check if success
            "url_field": "data.url",       // JSONPath to published URL
            "post_id_field": "data.id"     // JSONPath to platform post ID
        }
    }
    """

    def __init__(self, auth: ChannelAuth | None = None, config: dict | None = None):
        super().__init__(auth, config)
        self._api_config = (config or {}).get("api", {}) if config else {}

    @property
    def channel_type(self) -> str:
        return self._api_config.get("channel_type", "generic")

    @property
    def channel_name(self) -> str:
        return self._api_config.get("channel_name", "自定义渠道")

    @property
    def target_model(self) -> str:
        return self._api_config.get("target_model", "general")

    async def publish(self, content: PublishContent) -> PublishResult:
        """Publish using the configured HTTP API."""
        api = self._api_config
        if not api:
            return PublishResult(
                success=False, status="error",
                error_message="未配置API信息，请在渠道设置中填写API参数"
            )

        url = api.get("url", "")
        method = api.get("method", "POST").upper()
        auth_type = api.get("auth_type", "bearer")

        # Build headers
        headers = dict(api.get("headers", {}))
        headers["Content-Type"] = headers.get("Content-Type", "application/json")

        # Add auth header
        auth_header = api.get("auth_header", "Authorization")
        auth_prefix = api.get("auth_prefix", "Bearer ")
        if auth_type == "bearer":
            headers[auth_header] = f"{auth_prefix}{self.auth.access_token}"
        elif auth_type == "api_key":
            headers[auth_header] = self.auth.api_key or ""
        elif auth_type == "basic":
            import base64
            creds = base64.b64encode(
                f"{self.auth.api_key}:{self.auth.api_secret}".encode()
            ).decode()
            headers[auth_header] = f"Basic {creds}"
        elif auth_type == "header":
            # API key as a custom header
            headers[auth_header] = self.auth.api_key or ""

        # Build body from template
        body = self._render_template(api.get("body_template", {}), content)

        # Make request
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                if method == "GET":
                    resp = await client.get(url, headers=headers)
                elif method == "PUT":
                    resp = await client.put(url, headers=headers, json=body)
                elif method == "PATCH":
                    resp = await client.patch(url, headers=headers, json=body)
                else:  # POST
                    resp = await client.post(url, headers=headers, json=body)

                success = 200 <= resp.status_code < 300
                data = resp.json() if resp.text else {}

                # Extract fields using JSONPath-like dotted notation
                post_id = self._get_nested(data, api.get("post_id_field", ""))
                pub_url = self._get_nested(data, api.get("url_field", ""))

                return PublishResult(
                    success=success,
                    status="published" if success else "failed",
                    published_url=str(pub_url) if pub_url else None,
                    platform_post_id=str(post_id) if post_id else None,
                    raw_response=data,
                    error_message="" if success else f"HTTP {resp.status_code}: {resp.text[:200]}",
                )
        except Exception as e:
            return PublishResult(
                success=False, status="error",
                error_message=f"请求失败: {str(e)}"
            )

    async def validate_credentials(self) -> bool:
        """Test connectivity by making a lightweight request."""
        api = self._api_config
        if not api:
            return False
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                test_url = api.get("test_url", api.get("url", ""))
                if not test_url:
                    return bool(self.auth.access_token or self.auth.api_key)
                headers = {}
                auth_header = api.get("auth_header", "Authorization")
                headers[auth_header] = f"Bearer {self.auth.access_token}"
                resp = await client.get(test_url, headers=headers)
                return resp.status_code < 500
        except Exception:
            return bool(self.auth.access_token or self.auth.api_key)

    @staticmethod
    def _render_template(template: dict, content: PublishContent) -> dict:
        """Replace {{variables}} in template with actual content values."""
        import json as _json
        raw = _json.dumps(template)
        raw = raw.replace("{{title}}", _json.dumps(content.title)[1:-1])
        raw = raw.replace("{{body}}", _json.dumps(content.body_markdown)[1:-1])
        raw = raw.replace("{{summary}}", _json.dumps(content.summary or "")[1:-1])
        tags_str = ", ".join(content.tags) if content.tags else ""
        raw = raw.replace("{{tags}}", _json.dumps(tags_str)[1:-1])
        return _json.loads(raw)

    @staticmethod
    def _get_nested(data: dict, path: str):
        """Get nested dict value by dotted path: 'data.url' → data['data']['url']."""
        if not path or not data:
            return None
        parts = path.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list) and part.isdigit():
                idx = int(part)
                current = current[idx] if idx < len(current) else None
            else:
                return None
        return current

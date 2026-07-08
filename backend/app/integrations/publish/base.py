"""Channel adapter base class — unified interface for all publishing channels.

Each channel (Toutiao, Baijiahao, WeChat, CMS, etc.) implements this interface.
New channels can be added by subclassing without modifying the publish service.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ChannelAuth:
    """Authentication credentials for a publishing channel."""
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    app_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    extra: dict = field(default_factory=dict)


@dataclass
class PublishContent:
    """Content to be published to a channel."""
    title: str
    body_markdown: str
    body_html: Optional[str] = None
    cover_image_url: Optional[str] = None
    summary: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    original_url: Optional[str] = None  # Canonical URL for cross-reference


@dataclass
class PublishResult:
    """Result of a publish attempt."""
    success: bool
    published_url: Optional[str] = None
    platform_post_id: Optional[str] = None
    status: str = "unknown"  # success, failed, pending_review
    error_message: Optional[str] = None
    raw_response: Optional[dict] = None


class BaseChannelAdapter(ABC):
    """Abstract base class for all publishing channel adapters.

    Subclass this to add a new publishing channel. Only `publish()` must be
    implemented; the other methods have sensible defaults.
    """

    def __init__(self, auth: ChannelAuth | None = None, config: dict | None = None):
        self.auth = auth or ChannelAuth()  # Safe default for info-only usage
        self.config = config or {}

    @property
    @abstractmethod
    def channel_type(self) -> str:
        """Unique identifier for this channel type (e.g., 'toutiao', 'baijiahao')."""
        ...

    @property
    @abstractmethod
    def channel_name(self) -> str:
        """Human-readable channel name (e.g., '今日头条', '百家号')."""
        ...

    @property
    def target_model(self) -> str:
        """Which LLM model ecosystem this channel belongs to (for directional publishing)."""
        return "general"

    @abstractmethod
    async def publish(self, content: PublishContent) -> PublishResult:
        """Publish content to the channel. Must be implemented by subclasses."""
        ...

    async def get_status(self, post_id: str) -> PublishResult:
        """Query the status of a previously published post. Optional override."""
        return PublishResult(success=True, status="unknown", platform_post_id=post_id, published_url=None)

    async def delete(self, post_id: str) -> PublishResult:
        """Delete/retract a published post. Optional override."""
        return PublishResult(success=True, status="deleted", published_url=None)

    async def refresh_auth(self) -> ChannelAuth:
        """Refresh OAuth tokens if needed. Optional override."""
        return self.auth

    async def validate_credentials(self) -> bool:
        """Check if the current credentials are valid. Optional override."""
        return bool(self.auth.access_token or self.auth.api_key)


# ── Concrete Adapter Implementations ────────────────────────────


class ToutiaoAdapter(BaseChannelAdapter):
    """今日头条图文发布适配器 — 豆包生态权重提升."""

    @property
    def channel_type(self) -> str:
        return "toutiao"

    @property
    def channel_name(self) -> str:
        return "今日头条"

    @property
    def target_model(self) -> str:
        return "doubao"

    async def publish(self, content: PublishContent) -> PublishResult:
        """Publish to Toutiao via API. Requires app_id + access_token."""
        if not self.auth.access_token:
            return PublishResult(success=False, status="auth_error", error_message="Toutiao access_token not configured")

        try:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://open.toutiao.com/api/article/publish",
                    headers={"Authorization": f"Bearer {self.auth.access_token}"},
                    json={
                        "title": content.title,
                        "content": content.body_html or content.body_markdown,
                        "cover_image": content.cover_image_url,
                        "tags": content.tags,
                        "original_source": content.original_url,
                    },
                )
                data = resp.json()
                if resp.status_code == 200 and data.get("code") == 0:
                    return PublishResult(
                        success=True, published_url=data.get("data", {}).get("url"),
                        platform_post_id=str(data.get("data", {}).get("article_id")),
                        status="success", raw_response=data,
                    )
                return PublishResult(success=False, status="api_error", error_message=data.get("message", "Unknown error"), raw_response=data)
        except Exception as e:
            return PublishResult(success=False, status="network_error", error_message=str(e))


class BaijiahaoAdapter(BaseChannelAdapter):
    """百家号文章发布适配器 — 文心一言生态权重提升."""

    @property
    def channel_type(self) -> str:
        return "baijiahao"

    @property
    def channel_name(self) -> str:
        return "百家号"

    @property
    def target_model(self) -> str:
        return "wenxin"

    async def publish(self, content: PublishContent) -> PublishResult:
        if not self.auth.api_key:
            return PublishResult(success=False, status="auth_error", error_message="Baijiahao api_key not configured")

        try:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://baijiahao.baidu.com/api/article/publish",
                    headers={"X-API-Key": self.auth.api_key},
                    json={
                        "title": content.title,
                        "content": content.body_html or content.body_markdown,
                        "summary": content.summary,
                        "tags": ",".join(content.tags),
                        "cover_images": [content.cover_image_url] if content.cover_image_url else [],
                    },
                )
                data = resp.json()
                if resp.status_code == 200 and data.get("errno") == 0:
                    return PublishResult(
                        success=True, published_url=data.get("data", {}).get("url"),
                        platform_post_id=str(data.get("data", {}).get("id")),
                        status="success", raw_response=data,
                    )
                return PublishResult(success=False, status="api_error", error_message=data.get("errmsg", "Unknown error"), raw_response=data)
        except Exception as e:
            return PublishResult(success=False, status="network_error", error_message=str(e))


class WechatMPAdapter(BaseChannelAdapter):
    """微信公众号图文发布适配器 — 腾讯元宝生态权重提升."""

    @property
    def channel_type(self) -> str:
        return "wechat_mp"

    @property
    def channel_name(self) -> str:
        return "微信公众号"

    @property
    def target_model(self) -> str:
        return "yuanbao"

    async def publish(self, content: PublishContent) -> PublishResult:
        if not self.auth.access_token:
            return PublishResult(success=False, status="auth_error", error_message="WeChat access_token not configured")

        try:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.weixin.qq.com/cgi-bin/material/add_news",
                    params={"access_token": self.auth.access_token},
                    json={
                        "articles": [{
                            "title": content.title,
                            "content": content.body_html or content.body_markdown,
                            "digest": content.summary,
                            "content_source_url": content.original_url or "",
                            "thumb_media_id": content.cover_image_url or "",
                        }]
                    },
                )
                data = resp.json()
                if resp.status_code == 200 and "media_id" in data:
                    return PublishResult(
                        success=True, platform_post_id=data.get("media_id"),
                        status="success", raw_response=data,
                    )
                return PublishResult(success=False, status="api_error", error_message=data.get("errmsg", "Unknown error"), raw_response=data)
        except Exception as e:
            return PublishResult(success=False, status="network_error", error_message=str(e))


class CMSAdapter(BaseChannelAdapter):
    """通用CMS/企业官网发布适配器."""

    @property
    def channel_type(self) -> str:
        return "cms"

    @property
    def channel_name(self) -> str:
        return "企业官网CMS"

    @property
    def target_model(self) -> str:
        return "general"

    async def publish(self, content: PublishContent) -> PublishResult:
        cms_url = self.config.get("api_url")
        cms_token = self.auth.api_key
        if not cms_url or not cms_token:
            return PublishResult(success=False, status="auth_error", error_message="CMS URL or API key not configured")

        try:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    cms_url,
                    headers={"Authorization": f"Bearer {cms_token}", "Content-Type": "application/json"},
                    json={
                        "title": content.title,
                        "content": content.body_html or content.body_markdown,
                        "excerpt": content.summary,
                        "tags": content.tags,
                        "status": "publish",
                    },
                )
                data = resp.json()
                if resp.status_code in (200, 201):
                    return PublishResult(
                        success=True, published_url=data.get("url") or data.get("link"),
                        platform_post_id=str(data.get("id")), status="success", raw_response=data,
                    )
                return PublishResult(success=False, status="api_error", error_message=str(data), raw_response=data)
        except Exception as e:
            return PublishResult(success=False, status="network_error", error_message=str(e))


# ── Adapter Registry ────────────────────────────────────────────

ADAPTER_REGISTRY: dict[str, type[BaseChannelAdapter]] = {
    "toutiao": ToutiaoAdapter,
    "baijiahao": BaijiahaoAdapter,
    "wechat_mp": WechatMPAdapter,
    "cms": CMSAdapter,
}


def get_adapter(channel_type: str, auth: ChannelAuth, config: dict | None = None) -> BaseChannelAdapter:
    """Factory: instantiate the correct adapter for a channel type.

    If the channel type is not in the registry but has API config in config_json,
    falls back to GenericHttpAdapter for UI-configured custom channels.
    """
    adapter_cls = ADAPTER_REGISTRY.get(channel_type)
    if adapter_cls:
        return adapter_cls(auth, config)

    # Fallback: use GenericHttpAdapter for custom UI-configured channels
    if config and config.get("api"):
        from app.integrations.publish.generic_adapter import GenericHttpAdapter
        return GenericHttpAdapter(auth, config)
    raise ValueError(f"Unknown channel type: {channel_type}. Available: {list(ADAPTER_REGISTRY.keys())}")

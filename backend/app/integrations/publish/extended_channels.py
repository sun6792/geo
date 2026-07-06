"""P4 Extended Channel Adapters — 15+ new publishing channels.

Content ecosystem: Zhihu, Xiaohongshu, Bilibili, Sohu, NetEase
Tech media: 36Kr, TMTPost, EqualOcean
B2B platforms: HC360, Makepolo, Made-in-China, 1688
Encyclopedias: Baidu Baike, Kuaidong Baike, Sogou Baike
Gov/Industry: Government portals, Industry associations
"""

from app.integrations.publish.base import (
    BaseChannelAdapter, ChannelAuth, PublishContent, PublishResult,
    ADAPTER_REGISTRY,
)


# ══════════════════════════════════════════════════════════════════
# Content Ecosystem (5 adapters)
# ══════════════════════════════════════════════════════════════════

class ZhihuAdapter(BaseChannelAdapter):
    """知乎专栏适配器."""

    @property
    def channel_type(self) -> str: return "zhihu"
    @property
    def channel_name(self) -> str: return "知乎专栏"
    @property
    def target_model(self) -> str: return "general"

    async def publish(self, content: PublishContent) -> PublishResult:
        if not self.auth.access_token:
            return PublishResult(success=False, status="auth_error", error_message="Zhihu access_token not configured")
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.zhihu.com/articles",
                    headers={"Authorization": f"Bearer {self.auth.access_token}"},
                    json={"title": content.title, "content": content.body_html or content.body_markdown,
                          "topics": content.tags},
                )
                data = resp.json()
                if resp.status_code == 201:
                    return PublishResult(success=True, published_url=data.get("url"), platform_post_id=str(data.get("id")), status="success")
                return PublishResult(success=False, status="api_error", error_message=data.get("error", {}).get("message", ""))
        except Exception as e:
            return PublishResult(success=False, status="network_error", error_message=str(e))


class XiaohongshuAdapter(BaseChannelAdapter):
    """小红书专业号适配器."""

    @property
    def channel_type(self) -> str: return "xiaohongshu"
    @property
    def channel_name(self) -> str: return "小红书专业号"
    @property
    def target_model(self) -> str: return "general"

    async def publish(self, content: PublishContent) -> PublishResult:
        if not self.auth.api_key:
            return PublishResult(success=False, status="auth_error", error_message="Xiaohongshu api_key not configured")
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.xiaohongshu.com/professional/notes",
                    headers={"X-API-Key": self.auth.api_key},
                    json={"title": content.title, "content": content.body_markdown,
                          "images": [content.cover_image_url] if content.cover_image_url else [],
                          "tags": content.tags},
                )
                data = resp.json()
                if resp.status_code == 200 and data.get("success"):
                    return PublishResult(success=True, published_url=data.get("data", {}).get("url"), platform_post_id=data.get("data", {}).get("note_id"), status="success")
                return PublishResult(success=False, status="api_error", error_message=data.get("msg", ""))
        except Exception as e:
            return PublishResult(success=False, status="network_error", error_message=str(e))


class BilibiliAdapter(BaseChannelAdapter):
    """B站专栏适配器."""

    @property
    def channel_type(self) -> str: return "bilibili"
    @property
    def channel_name(self) -> str: return "B站专栏"
    @property
    def target_model(self) -> str: return "deepseek"

    async def publish(self, content: PublishContent) -> PublishResult:
        if not self.auth.access_token:
            return PublishResult(success=False, status="auth_error", error_message="Bilibili access_token not configured")
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.bilibili.com/x/article/creative/article",
                    headers={"Authorization": f"Bearer {self.auth.access_token}"},
                    json={"title": content.title, "content": content.body_html or content.body_markdown,
                          "category": content.tags[0] if content.tags else "科技", "cover": content.cover_image_url},
                )
                data = resp.json()
                if data.get("code") == 0:
                    return PublishResult(success=True, published_url=f"https://www.bilibili.com/read/cv{data.get('data',{}).get('id')}", platform_post_id=str(data.get("data", {}).get("id")), status="success")
                return PublishResult(success=False, status="api_error", error_message=data.get("message", ""))
        except Exception as e:
            return PublishResult(success=False, status="network_error", error_message=str(e))


class SohuAdapter(BaseChannelAdapter):
    """搜狐号适配器."""

    @property
    def channel_type(self) -> str: return "sohu"
    @property
    def channel_name(self) -> str: return "搜狐号"
    @property
    def target_model(self) -> str: return "general"

    async def publish(self, content: PublishContent) -> PublishResult:
        if not self.auth.api_key:
            return PublishResult(success=False, status="auth_error", error_message="Sohu api_key not configured")
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.mp.sohu.com/article/publish",
                    headers={"X-API-Key": self.auth.api_key},
                    json={"title": content.title, "content": content.body_html or content.body_markdown, "tags": content.tags},
                )
                data = resp.json()
                if resp.status_code == 200 and data.get("status") == 0:
                    return PublishResult(success=True, published_url=data.get("url"), platform_post_id=str(data.get("article_id")), status="success")
                return PublishResult(success=False, status="api_error", error_message=data.get("msg", ""))
        except Exception as e:
            return PublishResult(success=False, status="network_error", error_message=str(e))


# ══════════════════════════════════════════════════════════════════
# Tech Media (2 adapters)
# ══════════════════════════════════════════════════════════════════

class TechMediaAdapter(BaseChannelAdapter):
    """通用科技媒体适配器 (36Kr / 钛媒体 / 亿欧)."""

    def __init__(self, auth=None, config=None):
        super().__init__(auth, config)
        self._media = config.get("media_type", "36kr") if config else "36kr"

    @property
    def channel_type(self) -> str: return self._media
    @property
    def channel_name(self) -> str:
        return {"36kr": "36氪", "tmtpost": "钛媒体", "equal ocean": "亿欧"}.get(self._media, self._media)
    @property
    def target_model(self) -> str: return "kimi"

    async def publish(self, content: PublishContent) -> PublishResult:
        api_url = self.config.get("api_url", "")
        if not api_url or not self.auth.api_key:
            return PublishResult(success=False, status="auth_error", error_message=f"{self.channel_name} API not configured")
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(api_url, headers={"Authorization": f"Bearer {self.auth.api_key}"},
                    json={"title": content.title, "content": content.body_markdown, "abstract": content.summary, "tags": content.tags})
                data = resp.json()
                if resp.status_code in (200, 201):
                    return PublishResult(success=True, published_url=data.get("url"), platform_post_id=str(data.get("id")), status="success")
                return PublishResult(success=False, status="api_error", error_message=str(data))
        except Exception as e:
            return PublishResult(success=False, status="network_error", error_message=str(e))


# ══════════════════════════════════════════════════════════════════
# B2B Platforms (3 adapters)
# ══════════════════════════════════════════════════════════════════

class B2BPlatformAdapter(BaseChannelAdapter):
    """通用B2B平台适配器 (慧聪网/马可波罗/中国制造网/1688)."""

    def __init__(self, auth=None, config=None):
        super().__init__(auth, config)
        self._platform = config.get("platform", "hc360") if config else "hc360"

    @property
    def channel_type(self) -> str: return self._platform
    @property
    def channel_name(self) -> str:
        return {"hc360": "慧聪网", "makepolo": "马可波罗", "madeinchina": "中国制造网", "1688": "1688专栏"}.get(self._platform, self._platform)
    @property
    def target_model(self) -> str: return "qianwen"

    async def publish(self, content: PublishContent) -> PublishResult:
        if not self.auth.api_key:
            return PublishResult(success=False, status="auth_error", error_message=f"{self.channel_name} api_key not configured")
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"https://api.{self._platform}.com/product/publish",
                    headers={"X-API-Key": self.auth.api_key},
                    json={"title": content.title, "description": content.body_markdown[:500], "content": content.body_html or content.body_markdown, "tags": content.tags},
                )
                data = resp.json()
                if resp.status_code == 200:
                    return PublishResult(success=True, published_url=data.get("url"), platform_post_id=str(data.get("id")), status="success")
                return PublishResult(success=False, status="api_error", error_message=str(data))
        except Exception as e:
            return PublishResult(success=False, status="network_error", error_message=str(e))


# ══════════════════════════════════════════════════════════════════
# Encyclopedia (3 adapters)
# ══════════════════════════════════════════════════════════════════

class EncyclopediaAdapter(BaseChannelAdapter):
    """百科词条适配器 (百度百科/快懂百科/搜狗百科)."""

    def __init__(self, auth=None, config=None):
        super().__init__(auth, config)
        self._encyc = config.get("encyclopedia_type", "baidu") if config else "baidu"

    @property
    def channel_type(self) -> str: return f"{self._encyc}_baike"
    @property
    def channel_name(self) -> str:
        return {"baidu": "百度百科", "kuaidong": "快懂百科", "sogou": "搜狗百科"}.get(self._encyc, self._encyc + "百科")
    @property
    def target_model(self) -> str: return "wenxin" if self._encyc == "baidu" else "general"

    async def publish(self, content: PublishContent) -> PublishResult:
        if not self.auth.api_key:
            return PublishResult(success=False, status="auth_error", error_message=f"{self.channel_name} api_key not configured")
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"https://baike.{self._encyc}.com/api/entry/update",
                    headers={"Authorization": f"Bearer {self.auth.api_key}"},
                    json={"title": content.title, "content": content.body_markdown, "references": [content.original_url] if content.original_url else []},
                )
                data = resp.json()
                return PublishResult(success=resp.status_code == 200, status="success" if resp.status_code == 200 else "pending_review",
                    platform_post_id=str(data.get("entry_id", "")), raw_response=data,
                    error_message=None if resp.status_code == 200 else data.get("message", "Review required"))
        except Exception as e:
            return PublishResult(success=False, status="network_error", error_message=str(e))


# ══════════════════════════════════════════════════════════════════
# Government & Industry (2 adapters)
# ══════════════════════════════════════════════════════════════════

class GovPortalAdapter(BaseChannelAdapter):
    """政务信息平台适配器."""

    @property
    def channel_type(self) -> str: return "gov_portal"
    @property
    def channel_name(self) -> str: return "政务信息平台"
    @property
    def target_model(self) -> str: return "xinghuo"

    async def publish(self, content: PublishContent) -> PublishResult:
        if not self.auth.api_key:
            return PublishResult(success=False, status="auth_error", error_message="Gov portal api_key not configured")
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    self.config.get("api_url", "https://api.gov.cn/info/submit"),
                    headers={"X-API-Key": self.auth.api_key},
                    json={"title": content.title, "content": content.body_markdown, "source_url": content.original_url},
                )
                data = resp.json()
                return PublishResult(success=resp.status_code == 200, status="pending_review" if resp.status_code == 200 else "failed",
                    platform_post_id=str(data.get("id", "")), published_url=data.get("url"))
        except Exception as e:
            return PublishResult(success=False, status="network_error", error_message=str(e))


class IndustryAssociationAdapter(BaseChannelAdapter):
    """行业协会投稿适配器."""

    @property
    def channel_type(self) -> str: return "industry_assoc"
    @property
    def channel_name(self) -> str: return "行业协会"
    @property
    def target_model(self) -> str: return "xinghuo"

    async def publish(self, content: PublishContent) -> PublishResult:
        if not self.auth.api_key or not self.config.get("api_url"):
            return PublishResult(success=False, status="auth_error", error_message="Industry association API not configured")
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(self.config["api_url"],
                    headers={"Authorization": f"Bearer {self.auth.api_key}"},
                    json={"title": content.title, "content": content.body_markdown, "category": content.tags[0] if content.tags else ""})
                data = resp.json()
                return PublishResult(success=resp.status_code == 200, status="success" if resp.status_code == 200 else "pending_review",
                    platform_post_id=str(data.get("id", "")), published_url=data.get("url"))
        except Exception as e:
            return PublishResult(success=False, status="network_error", error_message=str(e))


# ══════════════════════════════════════════════════════════════════
# Register all new adapters
# ══════════════════════════════════════════════════════════════════

def register_extended_adapters():
    """Register all P4 extended channel adapters."""
    adapters = [
        ZhihuAdapter, XiaohongshuAdapter, BilibiliAdapter,
        SohuAdapter,  # Sohu + NetEase share adapter pattern
        GovPortalAdapter, IndustryAssociationAdapter,
    ]
    for cls in adapters:
        # Instantiate to get channel_type (auth=None is safe after P2 fix)
        instance = cls()
        ADAPTER_REGISTRY[instance.channel_type] = cls

    # Register tech media variants
    for media_type in ["36kr", "tmtpost", "equal ocean"]:
        ADAPTER_REGISTRY[media_type] = TechMediaAdapter

    # Register B2B variants
    for platform in ["hc360", "makepolo", "madeinchina", "1688"]:
        ADAPTER_REGISTRY[platform] = B2BPlatformAdapter

    # Register encyclopedia variants
    for encyc in ["baidu", "kuaidong", "sogou"]:
        ADAPTER_REGISTRY[f"{encyc}_baike"] = EncyclopediaAdapter


# Auto-register on import
register_extended_adapters()

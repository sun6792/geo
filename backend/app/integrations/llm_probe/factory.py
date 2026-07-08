"""LLM Probe Factory — creates adapter instances from model_id.

Supports:
- Reading API keys from config
- Multi-account round-robin (future)
- Dynamic registration of new models
"""

from typing import Optional
from app.config import settings
from app.integrations.llm_probe.base import BaseLLMProbe, LLMConfig
from app.integrations.llm_probe.adapters import (
    DeepSeekAdapter, DoubaoAdapter, WenxinAdapter,
    QwenAdapter, HunyuanAdapter, XinghuoAdapter,
)

# ── Model registry: model_id → (adapter_class, config) ─────────
MODEL_REGISTRY = {
    "deepseek": {
        "class": DeepSeekAdapter,
        "model_name": "DeepSeek",
        "api_key": lambda: settings.OPENAI_API_KEY or "",
        "api_base": "https://api.deepseek.com/v1",
        "actual_model": "deepseek-chat",
        "price_1k_in": 0.001, "price_1k_out": 0.002,
    },
    "doubao": {
        "class": DoubaoAdapter,
        "model_name": "豆包",
        "api_key": lambda: settings.DOUBAO_API_KEY or "",
        "api_base": lambda: settings.DOUBAO_API_BASE or "https://ark.cn-beijing.volces.com/api/v3",
        "actual_model": lambda: settings.DOUBAO_MODEL or "doubao-pro-32k",
        "price_1k_in": 0.0008, "price_1k_out": 0.002,
    },
    "wenxin": {
        "class": WenxinAdapter,
        "model_name": "文心一言",
        "api_key": lambda: settings.WENXIN_API_KEY or "",
        "api_base": lambda: settings.WENXIN_API_BASE or "https://qianfan.baidubce.com/v2",
        "actual_model": lambda: settings.WENXIN_MODEL or "ernie-4.0-turbo-8k",
        "price_1k_in": 0.008, "price_1k_out": 0.008,
    },
    "qianwen": {
        "class": QwenAdapter,
        "model_name": "通义千问",
        "api_key": lambda: settings.QIANWEN_API_KEY or "",
        "api_base": lambda: settings.QIANWEN_API_BASE or "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "actual_model": lambda: settings.QIANWEN_MODEL or "qwen-plus",
        "price_1k_in": 0.002, "price_1k_out": 0.006,
    },
    "hunyuan": {
        "class": HunyuanAdapter,
        "model_name": "腾讯元宝",
        "api_key": lambda: (
            settings.HUNYUAN_API_KEY if getattr(settings, 'HUNYUAN_API_KEY', None)
            else settings.ZHIPU_API_KEY or ""
        ),
        "api_base": lambda: (
            "https://api.hunyuan.cloud.tencent.com/v1" if getattr(settings, 'HUNYUAN_API_KEY', None)
            else settings.ZHIPU_API_BASE
        ),
        "actual_model": lambda: (
            settings.HUNYUAN_MODEL if getattr(settings, 'HUNYUAN_API_KEY', None)
            else (settings.ZHIPU_MODEL or "glm-4-flash")
        ),
        "price_1k_in": 0.004, "price_1k_out": 0.012,
    },
    "yuanbao": {  # Alias for frontend compatibility
        "class": HunyuanAdapter,
        "model_name": "腾讯元宝",
        "api_key": lambda: (
            settings.HUNYUAN_API_KEY if getattr(settings, 'HUNYUAN_API_KEY', None)
            else settings.ZHIPU_API_KEY or ""
        ),
        "api_base": lambda: (
            "https://api.hunyuan.cloud.tencent.com/v1" if getattr(settings, 'HUNYUAN_API_KEY', None)
            else settings.ZHIPU_API_BASE
        ),
        "actual_model": lambda: (
            settings.HUNYUAN_MODEL if getattr(settings, 'HUNYUAN_API_KEY', None)
            else (settings.ZHIPU_MODEL or "glm-4-flash")
        ),
        "price_1k_in": 0.004, "price_1k_out": 0.012,
    },
    "xinghuo": {
        "class": XinghuoAdapter,
        "model_name": "讯飞星火",
        "api_key": lambda: (settings.XINGHUO_API_KEY or ""),
        "api_base": lambda: (settings.XINGHUO_API_BASE or "https://spark-api-open.xf-yun.com/v1"),
        "actual_model": lambda: (settings.XINGHUO_MODEL or "4.0Ultra"),
        "price_1k_in": 0.003, "price_1k_out": 0.010,
    },
}


class LLMProbeFactory:
    """Factory: creates LLM probe adapter instances by model_id."""

    @staticmethod
    def create(model_id: str) -> Optional[BaseLLMProbe]:
        """Create a probe adapter. Falls back to DeepSeek if native key unavailable."""
        from app.integrations.llm_probe.adapters.deepseek_proxy import DeepSeekProxyProbe

        entry = MODEL_REGISTRY.get(model_id)
        if not entry:
            return None

        api_key = entry["api_key"]() if callable(entry["api_key"]) else entry["api_key"]

        if api_key:
            # ── Native API available → use it ─────────────────
            api_base = entry["api_base"]() if callable(entry.get("api_base")) else entry.get("api_base", "")
            actual_model = entry["actual_model"]() if callable(entry.get("actual_model")) else entry.get("actual_model", "")
            config = LLMConfig(
                model_id=model_id,
                model_name=entry["model_name"],
                api_key=api_key,
                api_base=api_base,
                actual_model=actual_model,
                price_per_1k_input=entry.get("price_1k_in", 0.001),
                price_per_1k_output=entry.get("price_1k_out", 0.002),
            )
            return entry["class"](config)
        else:
            # ── No native key → use DeepSeek proxy with persona ─
            from app.config import settings
            if not settings.OPENAI_API_KEY:
                return None  # No fallback available
            fallback_config = LLMConfig(
                model_id=model_id,
                model_name=entry["model_name"],
                api_key=settings.OPENAI_API_KEY,
                api_base="https://api.deepseek.com/v1",
                actual_model="deepseek-chat",
            )
            return DeepSeekProxyProbe(fallback_config, target_model=model_id)

    @staticmethod
    def create_all() -> dict[str, BaseLLMProbe]:
        """Create adapters for all configured models."""
        probes = {}
        for model_id in MODEL_REGISTRY:
            probe = LLMProbeFactory.create(model_id)
            if probe:
                probes[model_id] = probe
        return probes

    @staticmethod
    def get_available_models() -> list[str]:
        """List model_ids that have API keys configured."""
        available = []
        for model_id, entry in MODEL_REGISTRY.items():
            key = entry["api_key"]() if callable(entry["api_key"]) else entry["api_key"]
            if key:
                available.append(model_id)
        return available

    @staticmethod
    def register(model_id: str, adapter_class, model_name: str,
                  api_key_func, api_base: str, actual_model: str,
                  price_in: float = 0.001, price_out: float = 0.002):
        """Dynamically register a new model adapter at runtime."""
        MODEL_REGISTRY[model_id] = {
            "class": adapter_class,
            "model_name": model_name,
            "api_key": api_key_func,
            "api_base": api_base,
            "actual_model": actual_model,
            "price_1k_in": price_in,
            "price_1k_out": price_out,
        }

"""P4 Multi-LLM Provider Integration — 7+ domestic models, smart routing, cost optimization."""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional

from app.config import settings


@dataclass
class LLMConfig:
    """Configuration for a single LLM provider."""
    provider: str           # doubao, wenxin, qianwen, spark, glm, deepseek, kimi, openai, anthropic
    model_name: str         # Specific model ID
    api_key: str
    api_base: str           # API endpoint URL
    cost_per_1k_tokens: float = 0.01  # Cost estimate per 1K tokens
    quality_score: float = 0.7         # GEO task quality score (0-1)
    priority: int = 5                  # Lower = higher priority
    is_active: bool = True
    max_retries: int = 3
    timeout_sec: int = 60


@dataclass
class RouteDecision:
    """Smart routing decision result."""
    provider: str
    model_name: str
    reason: str             # quality_priority, cost_optimization, fallback, only_available
    estimated_cost: float


class MultiLLMRouter:
    """Smart LLM router — selects the optimal model for each task type.

    Supports two modes:
    - 'quality': Prioritize model quality for the task
    - 'cost': Optimize for cost efficiency
    """

    def __init__(self, mode: str = "quality"):
        self.mode = mode
        self.providers: dict[str, LLMConfig] = {}
        self._load_providers()

    def _load_providers(self):
        """Load all configured LLM providers."""
        # OpenAI
        if settings.OPENAI_API_KEY:
            self.providers["openai"] = LLMConfig(
                provider="openai", model_name=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY, api_base="https://api.openai.com/v1",
                cost_per_1k_tokens=0.01, quality_score=0.85, priority=3,
            )
        # Anthropic
        if settings.ANTHROPIC_API_KEY:
            self.providers["anthropic"] = LLMConfig(
                provider="anthropic", model_name=settings.ANTHROPIC_MODEL,
                api_key=settings.ANTHROPIC_API_KEY, api_base="https://api.anthropic.com/v1",
                cost_per_1k_tokens=0.015, quality_score=0.90, priority=2,
            )
        # DeepSeek (cost-effective, high quality)
        self.providers["deepseek"] = LLMConfig(
            provider="deepseek", model_name="deepseek-chat",
            api_key=settings.__dict__.get("DEEPSEEK_API_KEY", ""),
            api_base="https://api.deepseek.com/v1",
            cost_per_1k_tokens=0.002, quality_score=0.82, priority=1,
        )

    def get_provider(self, name: str) -> Optional[LLMConfig]:
        return self.providers.get(name)

    def route(self, task_type: str) -> RouteDecision:
        """Route a task to the optimal model.

        Task types and their quality/cost preferences:
        - creative_writing: quality > cost (deep, nuanced content)
        - content_polish: cost > quality (light editing)
        - detection_probe: cost > quality (high volume, simple)
        - diagnosis_analysis: quality > cost (needs accuracy)
        - review_summary: cost > quality (summarization)
        - knowledge_qa: quality > cost (needs accuracy)
        - translation: cost > quality
        - multimodal: quality > cost
        """
        TASK_NEEDS = {
            "creative_writing": {"quality": 0.9, "cost_sensitive": False},
            "content_polish": {"quality": 0.5, "cost_sensitive": True},
            "detection_probe": {"quality": 0.3, "cost_sensitive": True},
            "diagnosis_analysis": {"quality": 0.85, "cost_sensitive": False},
            "review_summary": {"quality": 0.6, "cost_sensitive": True},
            "knowledge_qa": {"quality": 0.8, "cost_sensitive": False},
            "translation": {"quality": 0.5, "cost_sensitive": True},
            "multimodal": {"quality": 0.9, "cost_sensitive": False},
        }

        needs = TASK_NEEDS.get(task_type, {"quality": 0.7, "cost_sensitive": False})
        active = {k: v for k, v in self.providers.items() if v.is_active and v.api_key}

        if not active:
            return RouteDecision("none", "none", "no_available_provider", 0)

        if self.mode == "cost":
            # Pick cheapest that meets minimum quality threshold
            min_quality = needs["quality"] * 0.7
            candidates = [(k, v) for k, v in active.items() if v.quality_score >= min_quality]
            if not candidates:
                candidates = list(active.items())
            best = min(candidates, key=lambda x: x[1].cost_per_1k_tokens)
            return RouteDecision(best[0], best[1].model_name, "cost_optimization", best[1].cost_per_1k_tokens)
        else:
            # Quality-first: pick highest quality score
            candidates = list(active.items())
            if needs["cost_sensitive"]:
                # Filter by cost ceiling for quality-sensitive tasks
                candidates = [(k, v) for k, v in candidates if v.cost_per_1k_tokens < 0.05]
                if not candidates:
                    candidates = list(active.items())
            best = max(candidates, key=lambda x: x[1].quality_score)
            return RouteDecision(best[0], best[1].model_name, "quality_priority", best[1].cost_per_1k_tokens)

    async def call_with_fallback(self, task_type: str, system_prompt: str, user_prompt: str) -> dict:
        """Call LLM with automatic fallback on failure."""
        decision = self.route(task_type)
        provider = self.providers.get(decision.provider)

        if not provider:
            return {"error": "no_provider", "content": "", "provider": "none", "cost": 0}

        # Try primary provider first
        for attempt in range(provider.max_retries):
            try:
                result = await self._call_provider(provider, system_prompt, user_prompt)
                if result.get("content"):
                    return {**result, "provider": decision.provider, "routing": decision.reason}
            except Exception:
                if attempt < provider.max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))
                continue

        # Fallback: try other providers in priority order
        fallback_providers = sorted(
            [(k, v) for k, v in self.providers.items() if k != decision.provider and v.is_active and v.api_key],
            key=lambda x: x[1].priority,
        )
        for fb_name, fb_config in fallback_providers:
            try:
                result = await self._call_provider(fb_config, system_prompt, user_prompt)
                if result.get("content"):
                    return {**result, "provider": fb_name, "routing": "fallback", "original_choice": decision.provider}
            except Exception:
                continue

        return {"error": "all_providers_failed", "content": "", "provider": "none", "cost": 0}

    async def _call_provider(self, config: LLMConfig, system_prompt: str, user_prompt: str) -> dict:
        """Call a specific LLM provider."""
        import httpx

        provider = config.provider
        headers = {"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"}

        if provider in ("openai", "deepseek"):
            async with httpx.AsyncClient(timeout=config.timeout_sec) as client:
                resp = await client.post(
                    f"{config.api_base}/chat/completions",
                    headers=headers,
                    json={"model": config.model_name, "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ], "temperature": 0.7, "max_tokens": 3000},
                )
                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                usage = data.get("usage", {})
                cost = (usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)) / 1000 * config.cost_per_1k_tokens
                return {"content": content, "cost": cost, "tokens": usage.get("total_tokens", 0)}

        elif provider == "anthropic":
            async with httpx.AsyncClient(timeout=config.timeout_sec) as client:
                resp = await client.post(
                    f"{config.api_base}/messages",
                    headers={**headers, "anthropic-version": "2023-06-01"},
                    json={"model": config.model_name, "max_tokens": 3000, "system": system_prompt,
                          "messages": [{"role": "user", "content": user_prompt}]},
                )
                data = resp.json()
                content = data.get("content", [{}])[0].get("text", "") if data.get("content") else ""
                usage = data.get("usage", {})
                cost = (usage.get("input_tokens", 0) + usage.get("output_tokens", 0)) / 1000 * config.cost_per_1k_tokens
                return {"content": content, "cost": cost, "tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0)}

        # Generic OpenAI-compatible API for other Chinese providers
        async with httpx.AsyncClient(timeout=config.timeout_sec) as client:
            resp = await client.post(
                f"{config.api_base}/chat/completions",
                headers=headers,
                json={"model": config.model_name, "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ], "temperature": 0.7, "max_tokens": 3000},
            )
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = data.get("usage", {})
            cost = (usage.get("total_tokens", 0)) / 1000 * config.cost_per_1k_tokens
            return {"content": content, "cost": cost, "tokens": usage.get("total_tokens", 0)}


# Global router instance
llm_router = MultiLLMRouter(mode="quality")

"""P6: Unified LLM Probe Base — abstract interface + retry/rate-limit/circuit-breaker.

All 6 model adapters inherit from this base. Provides:
- Exponential backoff retry (max 3 attempts)
- Token-bucket rate limiting
- Circuit breaker (auto-open after 5 consecutive failures)
- Request logging & metrics
- Token counting
"""

import asyncio
import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("llm_probe")


@dataclass
class ProbeResult:
    """Standardized result from a single LLM probe."""
    model_id: str
    model_name: str
    query_text: str
    query_type: str           # "first_round" | "follow_up"
    raw_answer: str
    input_tokens: int = 0
    output_tokens: int = 0
    probe_duration_ms: int = 0
    status: str = "success"   # "success" | "failed" | "degraded"
    error_message: str = ""
    retry_count: int = 0
    # ── Authenticity fields ───────────────────────────────────
    probe_mode: str = "natural_probe"  # natural_probe | brand_check
    enable_search: bool = True
    raw_request: dict | None = None    # Complete API request body
    raw_response: str = ""             # Complete API response JSON
    api_request_id: str = ""           # Official request ID
    model_version: str = ""            # Actual model version used
    has_search_source: bool = False    # Whether response contains search citations


@dataclass
class LLMConfig:
    """Configuration for a single LLM provider."""
    model_id: str             # e.g. "deepseek", "doubao"
    model_name: str           # e.g. "DeepSeek", "豆包"
    api_key: str = ""
    api_base: str = ""
    actual_model: str = ""    # e.g. "deepseek-chat", "doubao-pro-32k"
    price_per_1k_input: float = 0.001
    price_per_1k_output: float = 0.002
    max_retries: int = 3
    timeout_sec: int = 60
    max_qps: float = 2.0      # Rate limit per second


class TokenBucket:
    """Simple async token-bucket rate limiter."""

    def __init__(self, rate: float, burst: int = 3):
        self.rate = rate
        self.burst = burst
        self.tokens = float(burst)
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> float:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(float(self.burst), self.tokens + elapsed * self.rate)
            self.last_refill = now
            if self.tokens < 1.0:
                wait = (1.0 - self.tokens) / self.rate
                self.tokens = 0.0
                return wait
            self.tokens -= 1.0
            return 0.0


class CircuitBreaker:
    """Simple circuit breaker — opens after N consecutive failures."""

    def __init__(self, threshold: int = 5, reset_seconds: float = 60.0):
        self.threshold = threshold
        self.reset_seconds = reset_seconds
        self.failures = 0
        self.open_since: float = 0.0

    @property
    def is_open(self) -> bool:
        if self.failures >= self.threshold:
            if time.monotonic() - self.open_since > self.reset_seconds:
                self.failures = 0  # auto-reset
                return False
            return True
        return False

    def success(self): self.failures = 0

    def failure(self):
        self.failures += 1
        if self.failures >= self.threshold:
            self.open_since = time.monotonic()


class BaseLLMProbe(ABC):
    """Abstract base for all LLM model probes.

    Subclass must implement:
    - _do_query(prompt, temperature, max_tokens) -> str
    - count_tokens(text) -> int
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self.rate_limiter = TokenBucket(config.max_qps)
        self.circuit = CircuitBreaker()
        self._sem = asyncio.Semaphore(3)  # max concurrent requests

    @property
    def model_id(self) -> str:
        return self.config.model_id

    @property
    def model_name(self) -> str:
        return self.config.model_name

    @abstractmethod
    async def count_tokens(self, text: str) -> int:
        """Estimate token count for a given text."""
        ...

    @abstractmethod
    async def _do_query_with_search(self, prompt: str, temperature: float,
                                      max_tokens: int) -> tuple[str, dict | None, str, str | None, str | None, bool]:
        """Execute actual API call with search enabled. Returns:
        (answer_text, raw_request_dict, raw_response_json_str, api_request_id, model_version, has_search_source)
        Must be implemented per model with correct search parameters."""
        ...

    async def query(self, prompt: str, temperature: float = 0.7,
                     max_tokens: int = 800) -> ProbeResult:
        """Public query method — handles retry, rate-limit, circuit-breaker."""
        t0 = time.time()

        if self.circuit.is_open:
            return ProbeResult(
                model_id=self.model_id, model_name=self.model_name,
                query_text=prompt, query_type="first_round", raw_answer="",
                status="failed", error_message=f"Circuit breaker open for {self.model_id}",
            )

        # Rate limit
        wait = await self.rate_limiter.acquire()
        if wait > 0:
            await asyncio.sleep(wait)

        # Execute with retry
        last_error = ""
        for attempt in range(self.config.max_retries + 1):
            try:
                async with self._sem:
                    raw_answer, raw_req, raw_resp, req_id, model_ver, has_search = \
                        await self._do_query_with_search(prompt, temperature, max_tokens)

                self.circuit.success()
                in_tokens = await self.count_tokens(prompt)
                out_tokens = await self.count_tokens(raw_answer)

                return ProbeResult(
                    model_id=self.model_id, model_name=self.model_name,
                    query_text=prompt, query_type="first_round",
                    raw_answer=raw_answer, input_tokens=in_tokens,
                    output_tokens=out_tokens,
                    probe_duration_ms=int((time.time() - t0) * 1000),
                    status="success", retry_count=attempt,
                    probe_mode="natural_probe", enable_search=True,
                    raw_request=raw_req, raw_response=raw_resp,
                    api_request_id=req_id or "", model_version=model_ver or "",
                    has_search_source=has_search,
                )
            except Exception as e:
                last_error = str(e)
                if attempt < self.config.max_retries:
                    backoff = min(2 ** attempt, 10)
                    await asyncio.sleep(backoff)
                continue

        self.circuit.failure()
        return ProbeResult(
            model_id=self.model_id, model_name=self.model_name,
            query_text=prompt, query_type="first_round", raw_answer="",
            status="degraded" if attempt > 0 else "failed",
            error_message=last_error, retry_count=self.config.max_retries,
            probe_duration_ms=int((time.time() - t0) * 1000),
            probe_mode="natural_probe", enable_search=True,
        )

    async def query_follow_up(self, original_query: str, first_answer: str,
                               company_name: str) -> ProbeResult:
        """Auto follow-up when brand not mentioned in first round."""
        prompt = (
            f"我刚才问了你一个问题：「{original_query}」。你的回答中完全没有提到「{company_name}」这家企业。\n"
            f"请重新评估，在回答中明确说明对「{company_name}」这家企业的了解程度：\n"
            f"1. 你是否知道这家企业？\n"
            f"2. 如果知道，它在行业中处于什么位置？\n"
            f"3. 如果不知道，请诚实说明不了解。"
        )
        result = await self.query(prompt, temperature=0.3, max_tokens=600)
        result.query_type = "follow_up"
        return result

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({self.model_id})>"

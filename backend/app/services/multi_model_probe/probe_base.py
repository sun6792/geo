"""P6: Abstract probe interface with rate limiting, retry, and circuit breaker.

Defines the standard probe contract that all model-specific probes must implement.
Supports pluggable extension — new models only need to implement this interface.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ════════════════════════════════════════════════════════════════
# Data classes
# ════════════════════════════════════════════════════════════════

class ProbeStatus(Enum):
    """Probe execution status."""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    EMPTY_RESPONSE = "empty_response"
    API_ERROR = "api_error"


@dataclass
class ProbeRequest:
    """Standardized probe request."""
    question: str
    system_prompt: str
    model_key: str           # doubao, wenxin, qianwen, yuanbao, xinghuo
    model_cn: str            # 豆包, 文心一言, 通义千问, 腾讯元宝, 讯飞星火
    keyword: str
    keyword_type: str        # broad, product, comparison, scenario
    question_round: int = 1
    temperature: float = 0.7
    max_tokens: int = 800
    extra_params: dict = field(default_factory=dict)


@dataclass
class ProbeResponse:
    """Standardized probe response."""
    request: ProbeRequest
    response_text: str
    status: ProbeStatus = ProbeStatus.SUCCESS
    tokens_input: int = 0
    tokens_output: int = 0
    latency_ms: int = 0
    error_message: str = ""
    retry_count: int = 0
    is_fallback: bool = False
    api_provider: str = ""       # Which actual API was called
    api_model_id: str = ""       # Actual model ID used


# ════════════════════════════════════════════════════════════════
# Rate Limiter
# ════════════════════════════════════════════════════════════════

class RateLimiter:
    """Token-bucket rate limiter for API calls.

    Prevents hitting target model rate limits by controlling
    requests per second and concurrency levels.
    """

    def __init__(self,
                 max_requests_per_second: float = 2.0,
                 max_concurrent: int = 3,
                 burst_size: int = 5):
        self.max_rate = max_requests_per_second
        self.max_concurrent = max_concurrent
        self.burst_size = burst_size
        self._tokens = float(burst_size)
        self._last_refill = time.monotonic()
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._lock = asyncio.Lock()

    async def acquire(self) -> float:
        """Acquire permission to make a request. Returns wait time in seconds."""
        wait_time = 0.0

        # Token bucket rate limiting
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(float(self.burst_size),
                               self._tokens + elapsed * self.max_rate)
            self._last_refill = now

            if self._tokens < 1.0:
                wait_time = (1.0 - self._tokens) / self.max_rate
                self._tokens = 0.0
            else:
                self._tokens -= 1.0

        if wait_time > 0:
            await asyncio.sleep(wait_time)

        # Concurrency control
        await self._semaphore.acquire()
        return wait_time

    def release(self):
        """Release concurrency slot after request completes."""
        self._semaphore.release()

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, *args):
        self.release()


# ════════════════════════════════════════════════════════════════
# Abstract Probe Interface
# ════════════════════════════════════════════════════════════════

class BaseModelProbe(ABC):
    """Abstract base class for all model probes.

    Subclass for each target model (豆包, 文心, 千问, 元宝, 星火).
    Provides built-in rate limiting, retry, timeout, and circuit breaker.
    """

    # ── Subclass must define ───────────────────────────────────
    model_key: str = ""          # e.g., "doubao"
    model_cn: str = ""           # e.g., "豆包"
    ecosystem: str = ""          # e.g., "头条/抖音生态"
    default_persona: str = ""    # System prompt describing model behavior

    def __init__(self,
                 api_key: str,
                 api_base: str = "https://api.deepseek.com/v1",
                 rate_limiter: RateLimiter | None = None,
                 max_retries: int = 3,
                 timeout_sec: int = 60,
                 circuit_breaker_threshold: int = 5):
        self.api_key = api_key
        self.api_base = api_base
        self.rate_limiter = rate_limiter or RateLimiter()
        self.max_retries = max_retries
        self.timeout_sec = timeout_sec
        self._consecutive_failures = 0
        self._circuit_open = False
        self._circuit_threshold = circuit_breaker_threshold
        self._circuit_reset_time: float = 0.0

    # ════════════════════════════════════════════════════════════
    # Public API
    # ════════════════════════════════════════════════════════════

    async def probe(self, request: ProbeRequest) -> ProbeResponse:
        """Execute a single probe request with full error handling."""
        import time as _time
        t0 = _time.time()

        # Check circuit breaker
        if self._is_circuit_open():
            return ProbeResponse(
                request=request,
                response_text="",
                status=ProbeStatus.API_ERROR,
                error_message=f"Circuit breaker open for {self.model_key}",
                is_fallback=True,
            )

        # Rate limit
        wait_time = await self.rate_limiter.acquire()

        # Execute with retry
        last_error = ""
        for attempt in range(self.max_retries + 1):
            try:
                result = await self._execute_request(request)
                self.rate_limiter.release()
                self._on_success()
                result.retry_count = attempt
                result.latency_ms = int((_time.time() - t0) * 1000)
                return result
            except Exception as e:
                last_error = str(e)
                self.rate_limiter.release()

                if self._is_retryable(e) and attempt < self.max_retries:
                    backoff = min(2 ** attempt, 10)
                    await asyncio.sleep(backoff)
                    continue
                break

        # All retries exhausted
        self._on_failure()
        return ProbeResponse(
            request=request,
            response_text=self._fallback_response(request),
            status=ProbeStatus.FAILED,
            error_message=last_error,
            retry_count=self.max_retries,
            is_fallback=True,
            latency_ms=int((_time.time() - t0) * 1000),
        )

    async def probe_batch(self, requests: list[ProbeRequest]) -> list[ProbeResponse]:
        """Execute multiple probe requests concurrently with rate limiting."""
        tasks = [self.probe(req) for req in requests]
        return await asyncio.gather(*tasks, return_exceptions=False)

    # ════════════════════════════════════════════════════════════
    # Subclass must implement
    # ════════════════════════════════════════════════════════════

    @abstractmethod
    async def _execute_request(self, request: ProbeRequest) -> ProbeResponse:
        """Execute the actual API call. Must be implemented per model."""
        ...

    @abstractmethod
    def _build_system_prompt(self, request: ProbeRequest) -> str:
        """Build the model-specific system prompt for simulation."""
        ...

    # ════════════════════════════════════════════════════════════
    # Internal helpers
    # ════════════════════════════════════════════════════════════

    def _is_retryable(self, error: Exception) -> bool:
        """Determine if an error is retryable."""
        retryable_types = (
            asyncio.TimeoutError,
            ConnectionError,
            TimeoutError,
        )
        if isinstance(error, retryable_types):
            return True
        error_str = str(error).lower()
        retryable_keywords = ["timeout", "rate limit", "too many requests",
                              "server error", "503", "502", "429", "connection"]
        return any(kw in error_str for kw in retryable_keywords)

    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is open."""
        if self._circuit_open:
            if time.monotonic() - self._circuit_reset_time > 60:
                # Reset after 60s
                self._circuit_open = False
                self._consecutive_failures = 0
                return False
            return True
        return False

    def _on_success(self):
        """Reset failure counter on success."""
        self._consecutive_failures = 0

    def _on_failure(self):
        """Increment failure counter and potentially open circuit."""
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._circuit_threshold:
            self._circuit_open = True
            self._circuit_reset_time = time.monotonic()

    def _fallback_response(self, request: ProbeRequest) -> str:
        """Generate a fallback response when API is unavailable."""
        return (
            f"[{self.model_cn}] 关于「{request.question[:60]}...」的检索："
            f"当前服务暂不可用，建议稍后重试。该企业在{self.ecosystem}的公开信息收录有限。"
        )

    def __repr__(self):
        return f"<{self.__class__.__name__} model={self.model_key}>"

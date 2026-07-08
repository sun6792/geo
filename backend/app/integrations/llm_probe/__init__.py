"""P6: Agent 1 LLM Probe Module — unified multi-model probing framework.

Architecture:
  BaseLLMProbe (abstract) → 6 adapters (DeepSeek/Doubao/Wenxin/Qwen/Hunyuan/Xinghuo)
  LLMProbeFactory → creates adapters from model_id
  QueryGenerator → DeepSeek-powered human-like question generation
  ProbeResultParser → DeepSeek Function Calling structured extraction
  BatchProbeScheduler → orchestrates full multi-model detection workflow

Data:
  LLMProbeResult — raw probe records with structured extraction
  ProbeTaskProgress — real-time task progress tracking
"""

from app.integrations.llm_probe.base import BaseLLMProbe, LLMConfig, ProbeResult, TokenBucket, CircuitBreaker
from app.integrations.llm_probe.factory import LLMProbeFactory, MODEL_REGISTRY
from app.integrations.llm_probe.query_generator import QueryGenerator
from app.integrations.llm_probe.result_parser import ProbeResultParser
from app.integrations.llm_probe.unbiased_query_generator import UnbiasedQueryGenerator
from app.integrations.llm_probe.authentic_parser import AuthenticParser
from app.integrations.llm_probe.scheduler import BatchProbeScheduler
from app.integrations.llm_probe.models import LLMProbeResult, ProbeTaskProgress

__all__ = [
    "BaseLLMProbe", "LLMConfig", "ProbeResult", "TokenBucket", "CircuitBreaker",
    "LLMProbeFactory", "MODEL_REGISTRY",
    "QueryGenerator", "UnbiasedQueryGenerator",
    "ProbeResultParser", "AuthenticParser",
    "BatchProbeScheduler",
    "LLMProbeResult", "ProbeTaskProgress",
]

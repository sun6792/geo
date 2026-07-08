"""P6: Agent 5 — Self-Evolution Module."""

from app.services.self_evolution.evolution_engine import SelfEvolutionEngine
from app.services.self_evolution.models import (
    EvolutionMetric, CompetitorBenchmark, AssetGrowthSnapshot,
)

__all__ = [
    "SelfEvolutionEngine",
    "EvolutionMetric",
    "CompetitorBenchmark",
    "AssetGrowthSnapshot",
]

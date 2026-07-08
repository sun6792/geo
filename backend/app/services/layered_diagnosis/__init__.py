"""P6: Agent 2 — Layered Diagnosis Module.

Three-layer precise asset diagnosis + gap checklist + Agent 3 linkage.

Provides:
- ThreeLayerDiagnosisEngine: Rule-based + DeepSeek-powered scoring & gap detection
- GapToBriefConverter: One-click gap → Agent 3 ContentBrief
- EnhancedDiagnosisService: Full orchestration service
- Models: DiagnosisGap, GapToBriefMapping, DiagnosisRule, ScoreHistory
"""

from app.services.layered_diagnosis.three_layer_engine import (
    ThreeLayerDiagnosisEngine, FiveDimResult, GapItem, LayerScore,
)
from app.services.layered_diagnosis.brief_converter import GapToBriefConverter, BriefSpec
from app.services.layered_diagnosis.enhanced_service import EnhancedDiagnosisService
from app.services.layered_diagnosis.models import (
    DiagnosisGap, GapToBriefMapping, DiagnosisRule, ScoreHistory,
)

__all__ = [
    "ThreeLayerDiagnosisEngine",
    "FiveDimResult",
    "GapItem",
    "LayerScore",
    "GapToBriefConverter",
    "BriefSpec",
    "EnhancedDiagnosisService",
    "DiagnosisGap",
    "GapToBriefMapping",
    "DiagnosisRule",
    "ScoreHistory",
]

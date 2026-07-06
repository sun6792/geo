"""Pydantic schemas for P1 Agent modules (Detection, Diagnosis, Review, Rules)."""

import uuid
from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════════
# Agent 1: Detection
# ══════════════════════════════════════════════════════════════════

class DetectionTaskCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    keywords: list[dict] = Field(default_factory=list)
    target_models: list[str] = Field(default_factory=list)
    competitor_ids: list[uuid.UUID] = Field(default_factory=list)
    schedule_type: str = "manual"
    cron_expression: Optional[str] = None


class DetectionTaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[list[dict]] = None
    target_models: Optional[list[str]] = None
    competitor_ids: Optional[list[uuid.UUID]] = None
    schedule_type: Optional[str] = None
    cron_expression: Optional[str] = None
    is_active: Optional[bool] = None


class DetectionTaskResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    keywords: list
    target_models: list
    competitor_ids: list[uuid.UUID]
    schedule_type: str
    is_active: bool
    last_run_at: Optional[datetime] = None
    last_status: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DetectionResultResponse(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    model_name: str
    keyword: str
    keyword_type: str
    brand_mentioned: bool
    rank_position: Optional[int] = None
    recommendation_level: Optional[str] = None
    cited_sources: list
    exposure_count: int
    detected_at: datetime

    model_config = {"from_attributes": True}


class CompetitorCreate(BaseModel):
    name: str = Field(..., max_length=200)
    website: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class CompetitorResponse(BaseModel):
    id: uuid.UUID
    name: str
    website: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    tags: list
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SourceVerificationResponse(BaseModel):
    id: uuid.UUID
    source_name: str
    source_url: Optional[str] = None
    source_type: str
    field_name: str
    kb_value: Optional[str] = None
    source_value: Optional[str] = None
    is_consistent: bool
    conflict_level: Optional[str] = None
    verified_at: datetime

    model_config = {"from_attributes": True}


class SentimentResponse(BaseModel):
    id: uuid.UUID
    source_name: str
    title: str
    sentiment: str
    risk_level: Optional[str] = None
    is_alert: bool
    content_snippet: Optional[str] = None
    detected_at: datetime

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════
# Agent 2: Diagnosis
# ══════════════════════════════════════════════════════════════════

class DiagnosisReportResponse(BaseModel):
    id: uuid.UUID
    title: str
    report_type: str
    model_name: Optional[str] = None
    diagnosis_period_start: date
    diagnosis_period_end: date
    status: str
    summary: Optional[str] = None
    common_gaps: list
    platform_gaps: list
    recommendations: list
    report_json: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class FiveDimScoreResponse(BaseModel):
    id: uuid.UUID
    diagnosis_report_id: uuid.UUID
    model_name: Optional[str] = None
    identity_score: float
    source_score: float
    content_depth_score: float
    content_freshness_score: float
    cross_validation_score: float
    total_score: float

    model_config = {"from_attributes": True}


class OptimizationItemCreate(BaseModel):
    title: str = Field(..., max_length=300)
    description: Optional[str] = None
    category: str
    priority: str = "important"
    target_model: Optional[str] = None
    assigned_to: Optional[uuid.UUID] = None
    due_date: Optional[date] = None


class OptimizationItemUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[uuid.UUID] = None
    due_date: Optional[date] = None


class OptimizationItemResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    category: str
    priority: str
    status: str
    target_model: Optional[str] = None
    assigned_to: Optional[uuid.UUID] = None
    due_date: Optional[date] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════
# Agent 5: Weekly Review & GEO Rules
# ══════════════════════════════════════════════════════════════════

class WeeklyReviewResponse(BaseModel):
    id: uuid.UUID
    week_start: date
    week_end: date
    status: str
    report_markdown: Optional[str] = None
    report_json: Optional[dict] = None
    highlights: Optional[dict] = None
    recommendations: Optional[dict] = None
    kb_gap_analysis: Optional[dict] = None
    content_performance_summary: Optional[dict] = None
    generated_by: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class GeoRuleResponse(BaseModel):
    id: uuid.UUID
    model_name: str
    rule_name: str
    rule_category: str
    rule_content: str
    confidence: float
    evidence: list
    version: int
    is_latest: bool
    is_active: bool
    discovered_at: datetime

    model_config = {"from_attributes": True}


class GeoRuleUpdate(BaseModel):
    rule_content: Optional[str] = None
    confidence: Optional[float] = None
    is_active: Optional[bool] = None

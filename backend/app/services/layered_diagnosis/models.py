"""P6: Agent 2 Layered Diagnosis — enhanced ORM models.

Extends the existing DiagnosisReport/FiveDimScore/OptimizationItem with:
- DiagnosisGap: Granular gap items with three-layer classification
- GapToBriefMapping: Gap → ContentBrief conversion tracking
- DiagnosisRule: Configurable diagnosis rules per industry
- ScoreHistory: Historical score tracking for trend comparison
"""

import uuid
from datetime import datetime, timezone, date

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from app.core.db_types import UniversalUUID as UUID, UniversalJSON as JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ════════════════════════════════════════════════════════════════
# Diagnosis Gap (精准缺口清单)
# ════════════════════════════════════════════════════════════════

class DiagnosisGap(Base):
    """三层资产诊断缺口 — 精准到点位的修复缺口清单。

    Each gap is classified by:
    - Layer: basic (基础资产) / marketing (营销资产) / multimodal (多模态资产)
    - Category: specific deficiency type within layer
    - Impact weight: how much this gap affects AI model ranking
    - Priority: urgent / important / long_term

    This is the core output of Agent 2, directly driving Agent 3 content creation.
    """

    __tablename__ = "diagnosis_gaps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    diagnosis_report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("diagnosis_reports.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # ── Three-layer classification ─────────────────────────────
    layer: Mapped[str] = mapped_column(String(30), nullable=False)
    # basic / marketing / multimodal

    category: Mapped[str] = mapped_column(String(50), nullable=False)
    # basic: identity_conflict / info_missing / contact_inconsistent / qualification_gap
    # marketing: pain_point_missing / case_missing / comparison_missing / pitfall_guide_missing
    # multimodal: photo_missing / video_missing / infographic_missing / comment_coverage_low

    gap_name: Mapped[str] = mapped_column(String(300), nullable=False)
    # Human-readable gap name, e.g., "百度百科词条缺失导致身份权重降低"

    description: Mapped[str] = mapped_column(Text, nullable=False)
    # Detailed description of what's missing

    impact_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # 0-100 impact weight — how much this gap lowers the AI model score

    impact_explanation: Mapped[str | None] = mapped_column(Text)
    # DeepSeek-generated explanation of why this gap matters

    affected_models: Mapped[list] = mapped_column(JSONB, default=list)
    # Which LLM models are most affected: ["doubao", "wenxin", ...]

    # ── Recommended fix ────────────────────────────────────────
    fix_recommendation: Mapped[str | None] = mapped_column(Text)
    # What content to create to fix this gap

    content_type_needed: Mapped[str | None] = mapped_column(String(50))
    # What type of content: seo_article / ai_qa / video_script / product_page / encyclopedia / faq / case_study

    target_keywords: Mapped[list] = mapped_column(JSONB, default=list)
    # Recommended keywords for the fix content

    estimated_impact: Mapped[str | None] = mapped_column(String(50))
    # Expected score improvement: +5-10分 / +10-20分 / +20+分

    # ── Priority ───────────────────────────────────────────────
    priority: Mapped[str] = mapped_column(String(20), default="important")
    # urgent (directly causing rank drop) / important (affecting recommendation) / long_term (nice to have)

    priority_reason: Mapped[str | None] = mapped_column(Text)
    # Why this priority was assigned

    # ── Status ─────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(String(30), default="open")
    # open / in_progress / fixed / verified / skipped

    # ── Agent 3 linkage ────────────────────────────────────────
    converted_to_brief: Mapped[bool] = mapped_column(Boolean, default=False)
    linked_brief_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_briefs.id", ondelete="SET NULL"), nullable=True
    )

    # ── Human override ─────────────────────────────────────────
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )


# ════════════════════════════════════════════════════════════════
# Gap-to-Brief Mapping (缺口→创作Brief转换)
# ════════════════════════════════════════════════════════════════

class GapToBriefMapping(Base):
    """缺口→Brief转换记录 — 追踪诊断缺口到内容创作的转化链路。

    Tracks which gaps were converted to content briefs, with
    conversion metadata for quality feedback loop.
    """

    __tablename__ = "gap_to_brief_mappings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    gap_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("diagnosis_gaps.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    brief_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_briefs.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # ── Conversion metadata ────────────────────────────────────
    auto_generated: Mapped[bool] = mapped_column(Boolean, default=True)
    # True = AI auto-generated brief, False = manually created

    prompt_template_snapshot: Mapped[str | None] = mapped_column(Text)
    # The prompt used to generate the brief (for quality tracking)

    brief_generation_time_ms: Mapped[int | None] = mapped_column(Integer)

    # ── Quality feedback ────────────────────────────────────────
    content_published: Mapped[bool] = mapped_column(Boolean, default=False)
    gap_resolved_after_publish: Mapped[bool | None] = mapped_column(Boolean)
    # Did this gap get resolved after the content was published?
    score_improvement: Mapped[float | None] = mapped_column(Float)
    # Score change after content was published

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


# ════════════════════════════════════════════════════════════════
# Diagnosis Rule (可配置诊断规则)
# ════════════════════════════════════════════════════════════════

class DiagnosisRule(Base):
    """可配置诊断规则 — 支持不同行业/客户定制诊断标准。

    Industry-specific rules that determine:
    - Which dimensions to check
    - What weight each dimension carries
    - What severity thresholds trigger what priority
    """

    __tablename__ = "diagnosis_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=True, index=True  # NULL = global/default rule
    )
    industry: Mapped[str | None] = mapped_column(String(100), index=True)
    # Which industry this rule applies to; NULL = all industries

    rule_name: Mapped[str] = mapped_column(String(200), nullable=False)
    rule_category: Mapped[str] = mapped_column(String(50), nullable=False)
    # scoring / threshold / priority / content_mapping

    layer: Mapped[str] = mapped_column(String(30), nullable=False)
    # basic / marketing / multimodal

    dimension: Mapped[str] = mapped_column(String(100), nullable=False)
    # identity_consistency / info_completeness / pain_point_coverage / case_depth / etc.

    weight: Mapped[float] = mapped_column(Float, default=1.0)
    # Weight in the overall layer score (0-10)

    check_logic: Mapped[dict] = mapped_column(JSONB, default=dict)
    # {"type": "count_check", "field": "xxx", "threshold": 3, "operator": "lt"}
    # {"type": "coverage_check", "field": "xxx", "min_coverage_pct": 50}

    severity_thresholds: Mapped[dict] = mapped_column(JSONB, default=dict)
    # {"severe": {"score_below": 30}, "partial": {"score_below": 60}, "adequate": {"score_above": 60}}

    gap_template: Mapped[str | None] = mapped_column(Text)
    # Template for generating gap description: "缺少{field}导致{impact}"

    fix_template: Mapped[str | None] = mapped_column(Text)
    # Template for generating fix recommendation

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )


# ════════════════════════════════════════════════════════════════
# Score History (历史评分追踪)
# ════════════════════════════════════════════════════════════════

class ScoreHistory(Base):
    """历史评分追踪 — 记录每次诊断的五维评分变化趋势。

    Enables historical comparison: "本月身份分85，上月75，提升+10分"
    Used for trend charts in Agent 5 weekly reviews.
    """

    __tablename__ = "score_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    diagnosis_report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("diagnosis_reports.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # ── Five-dimension scores ──────────────────────────────────
    identity_score: Mapped[float] = mapped_column(Float, default=0.0)
    basic_asset_score: Mapped[float] = mapped_column(Float, default=0.0)
    marketing_asset_score: Mapped[float] = mapped_column(Float, default=0.0)
    multimodal_asset_score: Mapped[float] = mapped_column(Float, default=0.0)
    sentiment_score: Mapped[float] = mapped_column(Float, default=0.0)
    total_score: Mapped[float] = mapped_column(Float, default=0.0)

    # ── Gap counts ─────────────────────────────────────────────
    urgent_gaps: Mapped[int] = mapped_column(Integer, default=0)
    important_gaps: Mapped[int] = mapped_column(Integer, default=0)
    long_term_gaps: Mapped[int] = mapped_column(Integer, default=0)

    # ── Trends (vs previous diagnosis) ─────────────────────────
    total_score_change: Mapped[float | None] = mapped_column(Float)
    identity_score_change: Mapped[float | None] = mapped_column(Float)
    gaps_resolved_since_last: Mapped[int | None] = mapped_column(Integer)

    recorded_at: Mapped[date] = mapped_column(Date, default=date.today)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

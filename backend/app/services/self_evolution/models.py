"""P6: Self-Evolution models — Agent 5 enhanced tracking tables."""

import uuid
from datetime import datetime, timezone, date

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from app.core.db_types import UniversalUUID as UUID, UniversalJSON as JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EvolutionMetric(Base):
    """自进化效果追踪 — 记录每次策略调整前后的效果对比。

    Tracks: "Did the system get better after applying backflow strategies?"
    Each record captures before/after metrics for a specific strategy application.
    """

    __tablename__ = "evolution_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    source_backflow_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("backflow_records.id", ondelete="SET NULL"), nullable=True
    )

    target_agent: Mapped[str] = mapped_column(String(20), nullable=False)
    # agent1 / agent2 / agent3 / agent4

    strategy_description: Mapped[str] = mapped_column(Text, nullable=False)

    # ── Before/after metrics ───────────────────────────────────
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # e.g., "brand_mention_rate", "total_diagnosis_score", "content_gen_success_rate"

    value_before: Mapped[float] = mapped_column(Float, nullable=False)
    value_after: Mapped[float | None] = mapped_column(Float)
    change_pct: Mapped[float | None] = mapped_column(Float)

    improvement_observed: Mapped[bool | None] = mapped_column(Boolean)
    # True=got better, False=got worse, None=not yet measured

    measured_at: Mapped[date] = mapped_column(Date, default=date.today)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class CompetitorBenchmark(Base):
    """竞品对标快照 — 周期性的多维度竞品对比数据。

    Snapshot comparing client vs competitor across:
    source count, asset volume, AI exposure, sentiment health.
    """

    __tablename__ = "competitor_benchmarks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    weekly_review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("weekly_reviews.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    competitor_name: Mapped[str] = mapped_column(String(300), nullable=False)

    # ── Multi-dimension comparison ─────────────────────────────
    source_count_self: Mapped[int] = mapped_column(Integer, default=0)
    source_count_competitor: Mapped[int] = mapped_column(Integer, default=0)
    source_gap: Mapped[int] = mapped_column(Integer, default=0)

    asset_volume_self: Mapped[int] = mapped_column(Integer, default=0)
    asset_volume_competitor: Mapped[int] = mapped_column(Integer, default=0)
    asset_gap: Mapped[int] = mapped_column(Integer, default=0)

    exposure_score_self: Mapped[float] = mapped_column(Float, default=0.0)
    exposure_score_competitor: Mapped[float] = mapped_column(Float, default=0.0)
    exposure_gap: Mapped[float] = mapped_column(Float, default=0.0)

    sentiment_score_self: Mapped[float] = mapped_column(Float, default=0.0)
    sentiment_score_competitor: Mapped[float] = mapped_column(Float, default=0.0)

    # ── Strategy ───────────────────────────────────────────────
    competitor_weakness: Mapped[str | None] = mapped_column(Text)
    overtaking_strategy: Mapped[str | None] = mapped_column(Text)
    priority_target: Mapped[str | None] = mapped_column(String(30))
    # source / asset / exposure / sentiment — which dimension to attack first

    comparison_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    recorded_at: Mapped[date] = mapped_column(Date, default=date.today)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class AssetGrowthSnapshot(Base):
    """资产增厚快照 — 四类资产周期增量明细。

    Tracks: identity/basic/marketing/multimodal asset growth week-over-week.
    """

    __tablename__ = "asset_growth_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    weekly_review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("weekly_reviews.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # ── Identity trust growth ──────────────────────────────────
    trust_score_current: Mapped[float] = mapped_column(Float, default=0.0)
    trust_score_previous: Mapped[float] = mapped_column(Float, default=0.0)
    trust_score_change: Mapped[float | None] = mapped_column(Float)

    # ── Basic asset growth ─────────────────────────────────────
    basic_assets_current: Mapped[int] = mapped_column(Integer, default=0)
    basic_assets_previous: Mapped[int] = mapped_column(Integer, default=0)
    basic_assets_change: Mapped[int | None] = mapped_column(Integer)

    # ── Marketing asset growth ─────────────────────────────────
    marketing_assets_current: Mapped[int] = mapped_column(Integer, default=0)
    marketing_assets_previous: Mapped[int] = mapped_column(Integer, default=0)
    marketing_assets_change: Mapped[int | None] = mapped_column(Integer)

    # ── Multimodal asset growth ────────────────────────────────
    multimodal_assets_current: Mapped[int] = mapped_column(Integer, default=0)
    multimodal_assets_previous: Mapped[int] = mapped_column(Integer, default=0)
    multimodal_assets_change: Mapped[int | None] = mapped_column(Integer)

    # ── AI weight change estimate ──────────────────────────────
    estimated_ai_weight_gain: Mapped[float | None] = mapped_column(Float)
    # Estimated overall AI model weight increase (0-100)

    growth_summary: Mapped[str | None] = mapped_column(Text)
    recorded_at: Mapped[date] = mapped_column(Date, default=date.today)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

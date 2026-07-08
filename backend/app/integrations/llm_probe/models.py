"""P6: LLM Probe Result — dedicated table for Agent 1 raw probe data."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from app.core.db_types import UniversalUUID as UUID, UniversalJSON as JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LLMProbeResult(Base):
    """单次 LLM 探测的完整记录 — Agent 1 核心数据表。

    Each row = one question → one model → one answer, fully traceable.
    Structured fields (brand_mentioned, rank, competitors, errors, negative)
    are extracted by DeepSeek Function Calling from the raw answer.
    """

    __tablename__ = "llm_probe_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("detection_tasks.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # ── Probe identification ───────────────────────────────────
    model_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(50), nullable=False)

    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    query_type: Mapped[str] = mapped_column(String(20), nullable=False, default="first_round")
    # first_round / follow_up / natural_ranking / brand_verification / competitor_parity

    raw_answer: Mapped[str] = mapped_column(Text, nullable=False)

    # ── Structured extraction ──────────────────────────────────
    brand_mentioned: Mapped[bool] = mapped_column(Boolean, default=False)
    brand_rank: Mapped[int] = mapped_column(Integer, default=0)
    mentioned_competitors: Mapped[list] = mapped_column(JSONB, default=list)
    has_error_info: Mapped[bool] = mapped_column(Boolean, default=False)
    error_details: Mapped[list] = mapped_column(JSONB, default=list)
    has_negative: Mapped[bool] = mapped_column(Boolean, default=False)
    negative_details: Mapped[list] = mapped_column(JSONB, default=list)
    info_consistency_score: Mapped[int] = mapped_column(Integer, default=50)

    # ── Authenticity fields (P6) ───────────────────────────────
    probe_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="natural_probe")
    confidence: Mapped[float] = mapped_column(Float, nullable=True, default=1.0)
    has_search_source: Mapped[bool] = mapped_column(Boolean, nullable=True, default=False)
    search_engine_name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    query_variant_group: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw_request: Mapped[dict] = mapped_column(JSONB, nullable=True)
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    api_request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # ── Cost tracking ──────────────────────────────────────────
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)

    # ── Execution metadata ─────────────────────────────────────
    probe_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    probe_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="success")
    error_message: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self):
        return f"<LLMProbeResult {self.model_id}:{self.query_text[:20]} brand={'✓' if self.brand_mentioned else '✗'}>"


class ProbeTaskProgress(Base):
    """探测任务进度追踪表 — 实时更新任务执行状态."""

    __tablename__ = "probe_task_progress"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("detection_tasks.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    total_queries: Mapped[int] = mapped_column(Integer, default=0)
    completed_queries: Mapped[int] = mapped_column(Integer, default=0)
    failed_queries: Mapped[int] = mapped_column(Integer, default=0)
    skipped_queries: Mapped[int] = mapped_column(Integer, default=0)

    # Per-model breakdown
    model_progress: Mapped[dict] = mapped_column(JSONB, default=dict)
    # {"deepseek": {"total": 5, "done": 3, "failed": 1}, ...}

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

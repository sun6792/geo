"""P6: Multi-Model Probe Module — dedicated ORM models for raw responses,
structured extraction results, execution logs, and aggregate statistics.

All tables include tenant isolation (customer_id) and are designed to
support the five-model real Q&A probing workflow.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from app.core.db_types import UniversalUUID as UUID, UniversalJSON as JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ════════════════════════════════════════════════════════════════
# Raw Response Storage (模型原始回答存档)
# ════════════════════════════════════════════════════════════════

class ModelProbeResponse(Base):
    """单个模型的单次提问-回答原始记录。

    Stores every question-answer pair from each model probe,
    with full execution metadata for traceability and debugging.
    One DetectionTask → N ModelProbeResponses (one per model per keyword per round).
    """

    __tablename__ = "model_probe_responses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("detection_tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("detection_results.id", ondelete="SET NULL"), nullable=True
    )

    # ── Probe identification ───────────────────────────────────
    model_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # doubao / wenxin / qianwen / yuanbao / xinghuo
    model_cn: Mapped[str] = mapped_column(String(50), nullable=False)
    # 豆包 / 文心一言 / 通义千问 / 腾讯元宝 / 讯飞星火

    question_round: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # Which round of questioning (for multi-round probes)
    keyword: Mapped[str] = mapped_column(String(500), nullable=False)
    keyword_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # broad / product / comparison / scenario

    # ── Request ────────────────────────────────────────────────
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    # The exact question sent to the model
    system_prompt: Mapped[str | None] = mapped_column(Text)
    # The system prompt used (model-specific persona)
    request_params: Mapped[dict] = mapped_column(JSONB, default=dict)
    # {temperature, max_tokens, top_p, ...}

    # ── Response ───────────────────────────────────────────────
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Full raw response from the model
    response_length: Mapped[int] = mapped_column(Integer, default=0)
    # Character count of response
    tokens_input: Mapped[int | None] = mapped_column(Integer)
    tokens_output: Mapped[int | None] = mapped_column(Integer)
    api_latency_ms: Mapped[int | None] = mapped_column(Integer)
    # API round-trip time in milliseconds

    # ── Execution metadata ─────────────────────────────────────
    execution_status: Mapped[str] = mapped_column(String(20), nullable=False, default="success")
    # success / failed / timeout / rate_limited / empty_response
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    is_fallback_response: Mapped[bool] = mapped_column(Boolean, default=False)
    # True if this is a canned fallback (API failed)

    # ── API metadata ───────────────────────────────────────────
    api_provider: Mapped[str | None] = mapped_column(String(50))
    # Which actual API was called (deepseek / doubao / wenxin / etc.)
    api_model_id: Mapped[str | None] = mapped_column(String(100))
    # The actual model version ID returned

    probed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # ── Relationships ──────────────────────────────────────────
    extraction = relationship("ProbeExtraction", back_populates="response",
                              uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ModelProbeResponse {self.model_name}:{self.keyword[:20]} R{self.question_round}>"


# ════════════════════════════════════════════════════════════════
# Structured Extraction Result (DeepSeek解析结果)
# ════════════════════════════════════════════════════════════════

class ProbeExtraction(Base):
    """基于DeepSeek对单条模型回答的结构化解析结果。

    Extracts from each raw response:
    - Brand mention & ranking
    - Competitor mentions & preference
    - Information accuracy & conflicts
    - Negative content detection
    - Source citations
    - Sentiment analysis

    Supports human correction with audit trail.
    """

    __tablename__ = "probe_extractions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    response_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_probe_responses.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("detection_tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # ── Brand detection ────────────────────────────────────────
    brand_mentioned: Mapped[bool] = mapped_column(Boolean, default=False)
    brand_name_found: Mapped[str | None] = mapped_column(String(300))
    # The exact brand name as found in the response
    mention_count: Mapped[int] = mapped_column(Integer, default=0)
    # How many times the brand was mentioned
    rank_position: Mapped[int | None] = mapped_column(Integer)
    # Overall rank (1=first mentioned, None=not mentioned)
    rank_in_category: Mapped[int | None] = mapped_column(Integer)
    # Rank within the specific product/service category

    # ── Competitor detection ───────────────────────────────────
    competitors_mentioned: Mapped[list] = mapped_column(JSONB, default=list)
    # [{"name": "竞品A", "rank": 2, "recommended": true, "advantage": "价格更低"}]
    recommends_competitor: Mapped[bool] = mapped_column(Boolean, default=False)
    preferred_competitor: Mapped[str | None] = mapped_column(String(300))
    # Which competitor is preferred/recommended over the client
    competitor_advantage_summary: Mapped[str | None] = mapped_column(Text)

    # ── Information accuracy ───────────────────────────────────
    info_is_accurate: Mapped[bool] = mapped_column(Boolean, default=True)
    info_conflicts: Mapped[list] = mapped_column(JSONB, default=list)
    # [{"field": "成立年份", "response_value": "2015年", "kb_value": "2008年", "conflict_level": "critical"}]
    info_errors: Mapped[list] = mapped_column(JSONB, default=list)
    # Factual errors found in response about the client
    consistency_score: Mapped[float] = mapped_column(Float, default=1.0)
    # 0-1 score of how consistent the response is with known facts

    # ── Negative content ───────────────────────────────────────
    negative_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    negative_content: Mapped[str | None] = mapped_column(Text)
    # The specific negative text found
    negative_category: Mapped[str | None] = mapped_column(String(50))
    # complaint / quality_issue / legal / rumor / competitor_attack
    risk_level: Mapped[str | None] = mapped_column(String(20))
    # high / medium / low

    # ── Source citations ───────────────────────────────────────
    cited_sources: Mapped[list] = mapped_column(JSONB, default=list)
    # [{"name": "百度百科", "url": "...", "type": "high_authority", "relevance": 0.9}]
    source_count: Mapped[int] = mapped_column(Integer, default=0)
    authoritative_source_count: Mapped[int] = mapped_column(Integer, default=0)

    # ── Content quality ────────────────────────────────────────
    response_sentiment: Mapped[str | None] = mapped_column(String(20))
    # positive / neutral / negative / mixed
    response_completeness: Mapped[str | None] = mapped_column(String(20))
    # complete / partial / minimal
    keyword_coverage: Mapped[list] = mapped_column(JSONB, default=list)
    # Keywords from the question that appeared in the response
    has_recommendation: Mapped[bool] = mapped_column(Boolean, default=False)
    # Does the response actively recommend any vendor?

    # ── Parsing metadata ───────────────────────────────────────
    parser_model: Mapped[str | None] = mapped_column(String(100))
    # Which model performed the extraction (e.g., "deepseek-chat")
    parser_version: Mapped[str | None] = mapped_column(String(20))
    # Version of the parsing prompt template
    parsing_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    # 0-1 confidence in the extraction results
    parsing_raw_output: Mapped[str | None] = mapped_column(Text)
    # The raw JSON output from the parser LLM (for debugging)

    # ── Human correction ───────────────────────────────────────
    is_human_corrected: Mapped[bool] = mapped_column(Boolean, default=False)
    corrected_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    corrected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    correction_notes: Mapped[str | None] = mapped_column(Text)
    corrected_fields: Mapped[list] = mapped_column(JSONB, default=list)
    # [{"field": "rank_position", "old_value": 5, "new_value": 3, "reason": "..."}]

    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # ── Relationships ──────────────────────────────────────────
    response = relationship("ModelProbeResponse", back_populates="extraction")

    def __repr__(self):
        return f"<ProbeExtraction R{self.rank_position} brand={'✓' if self.brand_mentioned else '✗'}>"


# ════════════════════════════════════════════════════════════════
# Probe Execution Log (探测执行日志)
# ════════════════════════════════════════════════════════════════

class ProbeExecutionLog(Base):
    """探测任务执行日志 — 记录每次探测任务的完整执行过程。

    Tracks: task-level execution state, model-level progress,
    per-question timing, retry/error counts, overall statistics.
    """

    __tablename__ = "probe_execution_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("detection_tasks.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # ── Execution state ────────────────────────────────────────
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # pending / running / paused / completed / failed / cancelled
    total_questions: Mapped[int] = mapped_column(Integer, default=0)
    # Total number of questions to ask (models × keywords × rounds)
    completed_questions: Mapped[int] = mapped_column(Integer, default=0)
    successful_questions: Mapped[int] = mapped_column(Integer, default=0)
    failed_questions: Mapped[int] = mapped_column(Integer, default=0)
    retried_questions: Mapped[int] = mapped_column(Integer, default=0)

    # ── Timing ─────────────────────────────────────────────────
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_duration_ms: Mapped[int | None] = mapped_column(Integer)
    avg_latency_ms: Mapped[int | None] = mapped_column(Integer)
    max_latency_ms: Mapped[int | None] = mapped_column(Integer)

    # ── Per-model breakdown ────────────────────────────────────
    model_progress: Mapped[dict] = mapped_column(JSONB, default=dict)
    # {
    #   "doubao": {"status": "completed", "questions": 12, "success": 12, "failed": 0, "avg_latency_ms": 850},
    #   "wenxin": {"status": "running", "questions": 8, "success": 8, "failed": 0},
    #   ...
    # }

    # ── Error summary ──────────────────────────────────────────
    errors: Mapped[list] = mapped_column(JSONB, default=list)
    # [{"model": "doubao", "keyword": "xxx", "round": 2, "error": "timeout", "retried": 1}]

    # ── Rate limiting ──────────────────────────────────────────
    rate_limit_hits: Mapped[int] = mapped_column(Integer, default=0)
    total_wait_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    # Total time spent waiting due to rate limiting

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )


# ════════════════════════════════════════════════════════════════
# Probe Statistics (实测统计聚合)
# ════════════════════════════════════════════════════════════════

class ProbeStatistics(Base):
    """探测任务统计聚合表 — 分模型/分关键词维度的汇总统计。

    Pre-computed statistics for fast dashboard rendering.
    Updated after each probe task completes.
    """

    __tablename__ = "probe_statistics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("detection_tasks.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # ── Aggregation dimensions ─────────────────────────────────
    model_name: Mapped[str | None] = mapped_column(String(50), index=True)
    # NULL = overall/task-level aggregation
    keyword_type: Mapped[str | None] = mapped_column(String(30))
    # NULL = all keyword types

    # ── Brand metrics ──────────────────────────────────────────
    total_probes: Mapped[int] = mapped_column(Integer, default=0)
    brand_mentioned_count: Mapped[int] = mapped_column(Integer, default=0)
    brand_mention_rate: Mapped[float] = mapped_column(Float, default=0.0)
    # Percentage of probes where brand was mentioned
    avg_rank_position: Mapped[float | None] = mapped_column(Float)
    # Average rank when brand is mentioned
    median_rank_position: Mapped[float | None] = mapped_column(Float)

    # ── Competitor metrics ─────────────────────────────────────
    competitor_mention_count: Mapped[int] = mapped_column(Integer, default=0)
    competitor_preference_rate: Mapped[float] = mapped_column(Float, default=0.0)
    # % of probes where competitor was preferred
    top_competitors: Mapped[list] = mapped_column(JSONB, default=list)
    # [{"name": "竞品A", "mentions": 15, "preferred": 8}]

    # ── Quality metrics ────────────────────────────────────────
    info_error_count: Mapped[int] = mapped_column(Integer, default=0)
    negative_content_count: Mapped[int] = mapped_column(Integer, default=0)
    accuracy_rate: Mapped[float] = mapped_column(Float, default=1.0)
    # Percentage of responses with accurate information

    # ── Source metrics ─────────────────────────────────────────
    total_cited_sources: Mapped[int] = mapped_column(Integer, default=0)
    authoritative_sources: Mapped[int] = mapped_column(Integer, default=0)
    avg_sources_per_response: Mapped[float] = mapped_column(Float, default=0.0)

    # ── Exposure scoring ───────────────────────────────────────
    exposure_level: Mapped[str | None] = mapped_column(String(20))
    # dominant / high / moderate / low / invisible
    exposure_score: Mapped[float] = mapped_column(Float, default=0.0)
    # 0-100 composite exposure score

    # ── Sentiment ──────────────────────────────────────────────
    positive_count: Mapped[int] = mapped_column(Integer, default=0)
    neutral_count: Mapped[int] = mapped_column(Integer, default=0)
    negative_count: Mapped[int] = mapped_column(Integer, default=0)

    # ── Metadata ───────────────────────────────────────────────
    stats_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    # Full detailed stats for flexible querying
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    class Config:
        indexes = [
            {"columns": ["customer_id", "task_id", "model_name"]},
        ]

"""P1 Agent models — Detection, Diagnosis, Review, GEO Rules."""

import uuid
from datetime import datetime, timezone, date

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from app.core.db_types import UniversalUUID as UUID, UniversalJSON as JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ══════════════════════════════════════════════════════════════════
# Agent 1: Detection & Collection
# ══════════════════════════════════════════════════════════════════

class DetectionTask(Base):
    """探测任务配置 — 定义探测关键词、目标模型、竞品、调度规则."""

    __tablename__ = "detection_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    keywords: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # keywords structure: [{"word": "xxx", "type": "broad|product|comparison|scenario", "weight": 1.0}]
    target_models: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # target_models: ["doubao", "wenxin", "qianwen", "yuanbao", "xinghuo", "deepseek", "kimi"]
    competitor_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    schedule_type: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")  # manual, daily, weekly
    cron_expression: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[str | None] = mapped_column(String(30))
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    results = relationship("DetectionResult", back_populates="task", lazy="dynamic", cascade="all, delete-orphan")


class DetectionResult(Base):
    """探测结果 — 每次探测任务执行后，每个模型×关键词的返回数据."""

    __tablename__ = "detection_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("detection_tasks.id", ondelete="CASCADE"), nullable=False)
    model_name: Mapped[str] = mapped_column(String(50), nullable=False)  # doubao, wenxin, qianwen, yuanbao, xinghuo, deepseek, kimi
    keyword: Mapped[str] = mapped_column(String(500), nullable=False)
    keyword_type: Mapped[str] = mapped_column(String(30), nullable=False)  # broad, product, comparison, scenario
    brand_mentioned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rank_position: Mapped[int | None] = mapped_column(Integer)  # 排名位次，越小越好
    recommendation_level: Mapped[str | None] = mapped_column(String(20))  # high, medium, low, none
    cited_sources: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # cited_sources: [{"name": "百度百科", "url": "...", "type": "high_authority"}]
    exposure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    raw_response: Mapped[str | None] = mapped_column(Text)  # 原始返回内容摘要
    result_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    task = relationship("DetectionTask", back_populates="results")


class Competitor(Base):
    """竞品信息 — 客户配置的对标竞品."""

    __tablename__ = "competitors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    website: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    industry: Mapped[str | None] = mapped_column(String(100))
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class SourceVerification(Base):
    """信源校验结果 — 爬取企业公开信息后的一致性比对."""

    __tablename__ = "source_verifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    source_name: Mapped[str] = mapped_column(String(300), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2000))
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # official_website, encyclopedia, media, b2b, social
    field_name: Mapped[str] = mapped_column(String(200), nullable=False)  # 企业名称/产品参数/联系方式/地址
    kb_value: Mapped[str | None] = mapped_column(Text)  # 知识库中的值（唯一真值）
    source_value: Mapped[str | None] = mapped_column(Text)  # 信源上的值
    is_consistent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    conflict_level: Mapped[str | None] = mapped_column(String(20))  # critical, major, minor
    resolution: Mapped[str | None] = mapped_column(Text)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class SentimentResult(Base):
    """舆情监测结果."""

    __tablename__ = "sentiment_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    source_name: Mapped[str] = mapped_column(String(300), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2000))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content_snippet: Mapped[str | None] = mapped_column(Text)
    sentiment: Mapped[str] = mapped_column(String(20), nullable=False)  # positive, neutral, negative
    risk_level: Mapped[str | None] = mapped_column(String(20))  # high, medium, low
    is_alert: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # 是否触发预警
    keywords_matched: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════════
# Agent 2: Diagnosis & Analysis
# ══════════════════════════════════════════════════════════════════

class DiagnosisReport(Base):
    """诊断报告 — 分模型+整体诊断结论."""

    __tablename__ = "diagnosis_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    report_type: Mapped[str] = mapped_column(String(30), nullable=False)  # overall, per_model
    model_name: Mapped[str | None] = mapped_column(String(50))  # NULL for overall reports
    diagnosis_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    diagnosis_period_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")  # draft, published
    summary: Mapped[str | None] = mapped_column(Text)  # 诊断总结
    common_gaps: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # 通用短板
    platform_gaps: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # 平台专属短板
    recommendations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # 优化建议
    report_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)  # 完整结构化数据
    generated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class FiveDimScore(Base):
    """五维权重打分 — 每个诊断周期的五维评分."""

    __tablename__ = "five_dim_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    diagnosis_report_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("diagnosis_reports.id", ondelete="CASCADE"), nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(50))  # NULL = overall
    identity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # 身份权重
    source_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # 信源权重
    content_depth_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # 内容深度
    content_freshness_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # 内容新鲜度
    cross_validation_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # 交叉校验
    total_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    score_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class OptimizationItem(Base):
    """优化任务清单 — 基于诊断结果自动生成."""

    __tablename__ = "optimization_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    diagnosis_report_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("diagnosis_reports.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # kb_gap, content_creation, channel_expansion, rule_update
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="important")  # urgent, important, long_term
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")  # pending, in_progress, completed, skipped
    target_model: Mapped[str | None] = mapped_column(String(50))  # 关联大模型
    linked_content_brief_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))  # 关联的内容创作任务
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    due_date: Mapped[date | None] = mapped_column(Date)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════════
# Agent 5: Review & Rule Iteration
# ══════════════════════════════════════════════════════════════════

class WeeklyReviewMetric(Base):
    """周度复盘指标快照 — 每周核心指标的精确数值."""

    __tablename__ = "weekly_review_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    weekly_review_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("weekly_reviews.id", ondelete="CASCADE"), nullable=False)
    metric_type: Mapped[str] = mapped_column(String(50), nullable=False)  # exposure, recommendation, source, score, asset, competitor, sentiment
    metric_name: Mapped[str] = mapped_column(String(200), nullable=False)  # 豆包曝光涨幅, 文心推荐率变化, etc.
    model_name: Mapped[str | None] = mapped_column(String(50))
    current_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    previous_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    change_pct: Mapped[float | None] = mapped_column(Float)  # 变化百分比
    trend: Mapped[str | None] = mapped_column(String(10))  # up, down, stable
    metric_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class GeoRule(Base):
    """GEO规则库 — 反推各模型权重规则，支持版本历史."""

    __tablename__ = "geo_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=True, index=True)  # NULL = global
    model_name: Mapped[str] = mapped_column(String(50), nullable=False)
    rule_name: Mapped[str] = mapped_column(String(300), nullable=False)
    rule_category: Mapped[str] = mapped_column(String(50), nullable=False)  # ranking, recommendation, source_weight, content_quality, freshness
    rule_content: Mapped[str] = mapped_column(Text, nullable=False)  # 规则描述
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # 置信度 0-1
    evidence: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # 支撑数据
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_latest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

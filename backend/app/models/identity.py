"""P6: Enterprise Digital Identity Baseline & Data Backflow models.

Adds:
1. EnterpriseIdentityProfile — unified digital identity trust baseline
   (工商备案一致性, 官网Schema完整性, 蓝V/官号/百科/资质证书, 线下门店/厂区/地图实景)
2. ContentDerivative — tracks per-model differentiated content variants
3. BackflowRecord — Agent5→Agent1 data feedback loop records
4. MultimodalAsset — real photo/video/audio asset tracking separate from KB
5. CommentQA — comment section Q&A tracking for sentiment analysis
"""

import uuid
from datetime import datetime, timezone, date

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from app.core.db_types import UniversalUUID as UUID, UniversalJSON as JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ════════════════════════════════════════════════════════════════
# Enterprise Digital Identity Baseline (摘星身份可信度档案)
# ════════════════════════════════════════════════════════════════

class EnterpriseIdentityProfile(Base):
    """企业统一数字身份档案 — 一次性初始化后持续更新。

    Stores the complete identity verification baseline for an enterprise:
    - 工商备案一致性
    - 官网Schema结构化完整性
    - 蓝V/官号/百科/资质证书完整度
    - 线下门店/厂区/地图实景覆盖度
    - 综合身份可信度打分
    """

    __tablename__ = "enterprise_identity_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    company_name: Mapped[str] = mapped_column(String(300), nullable=False)

    # ── 工商备案一致性 ──────────────────────────────────────────
    business_license_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    business_license_number: Mapped[str | None] = mapped_column(String(100))
    legal_representative: Mapped[str | None] = mapped_column(String(100))
    registered_capital: Mapped[str | None] = mapped_column(String(50))
    business_scope: Mapped[str | None] = mapped_column(Text)
    establishment_date: Mapped[date | None] = mapped_column(Date)
    business_status: Mapped[str | None] = mapped_column(String(30))  # 存续/在业/吊销/注销
    business_license_issues: Mapped[list] = mapped_column(JSONB, default=list)

    # ── 官网Schema结构化 ────────────────────────────────────────
    official_website: Mapped[str | None] = mapped_column(String(500))
    website_schema_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    schema_types_found: Mapped[list] = mapped_column(JSONB, default=list)
    # e.g., ["Organization", "Product", "ContactPage", "FAQPage"]
    website_has_ssl: Mapped[bool] = mapped_column(Boolean, default=False)
    website_issues: Mapped[list] = mapped_column(JSONB, default=list)

    # ── 蓝V/官号/百科/资质证书 ──────────────────────────────────
    blue_v_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    blue_v_platforms: Mapped[list] = mapped_column(JSONB, default=list)
    # e.g., ["抖音企业号", "百家号认证", "微信公众号认证", "头条企业号"]

    encyclopedia_entries: Mapped[list] = mapped_column(JSONB, default=list)
    # e.g., [{"platform": "百度百科", "url": "...", "quality_score": 80}]

    certifications: Mapped[list] = mapped_column(JSONB, default=list)
    # e.g., [{"name": "ISO9001", "issuer": "...", "valid_until": "2027-01-01"}]

    patents_count: Mapped[int] = mapped_column(Integer, default=0)
    trademarks_count: Mapped[int] = mapped_column(Integer, default=0)

    # ── 线下门店/厂区/地图实景 ──────────────────────────────────
    offline_locations_count: Mapped[int] = mapped_column(Integer, default=0)
    offline_locations: Mapped[list] = mapped_column(JSONB, default=list)
    # e.g., [{"type": "factory", "address": "...", "area_sqm": 5000}]

    map_coverage_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    map_platforms: Mapped[list] = mapped_column(JSONB, default=list)
    # e.g., ["高德地图", "百度地图", "腾讯地图"]

    # ── 综合评分 ────────────────────────────────────────────────
    trust_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100
    identity_completeness_pct: Mapped[float] = mapped_column(Float, default=0.0)  # 身份完整度%
    last_verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    verification_source: Mapped[str | None] = mapped_column(String(50))  # deepseek/manual/gov_api
    raw_verification_data: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )


# ════════════════════════════════════════════════════════════════
# Content Derivatives (分模型差异化内容产物)
# ════════════════════════════════════════════════════════════════

class ContentDerivative(Base):
    """内容衍生品 — 从主稿衍生的分模型/分格式版本。

    One master draft produces N derivatives:
    - 3 format variants: SEO版, AI问答版, 短视频脚本版
    - 5 model-specific: 豆包版, 文心版, 千问版, 元宝版, 星火版
    """

    __tablename__ = "content_derivatives"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    source_draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_drafts.id", ondelete="CASCADE"), nullable=False
    )
    derivative_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # format: seo / ai_qa / short_video_script
    # model: doubao / wenxin / qianwen / yuanbao / xinghuo
    # ancillary: photo_captions / qa_replies / clarification

    target_model: Mapped[str | None] = mapped_column(String(50))
    # For model-specific variants: doubao/wenxin/qianwen/yuanbao/xinghuo
    # NULL for format variants and ancillary content

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    generation_prompt: Mapped[str | None] = mapped_column(Text)
    generation_model: Mapped[str | None] = mapped_column(String(100))  # e.g., "deepseek-chat"
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    generation_time_ms: Mapped[float] = mapped_column(Float, default=0.0)

    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft/published/archived
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationship
    source_draft = relationship("ContentDraft", backref="derivatives", foreign_keys=[source_draft_id])


# ════════════════════════════════════════════════════════════════
# Data Backflow Record (Agent5→Agent1 数据回流自进化)
# ════════════════════════════════════════════════════════════════

class BackflowRecord(Base):
    """数据回流记录 — Agent5 复盘结论反向输入 Agent1 优化探测策略。

    When Agent5 generates a weekly review, any detected:
    - New competitor keywords
    - Emerging content gaps
    - Model behavior changes
    - Sentiment pattern shifts

    ...are recorded here and automatically feed into the next detection cycle.
    """

    __tablename__ = "backflow_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    source_weekly_review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("weekly_reviews.id", ondelete="SET NULL"), nullable=True
    )
    source_rule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("geo_rules.id", ondelete="SET NULL"), nullable=True
    )

    backflow_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # keyword_optimization / model_targeting / content_gap / sentiment_alert / rule_update

    description: Mapped[str] = mapped_column(Text, nullable=False)

    # What changed
    old_value: Mapped[dict] = mapped_column(JSONB, default=dict)
    new_value: Mapped[dict] = mapped_column(JSONB, default=dict)

    # How it affects detection
    affected_keywords: Mapped[list] = mapped_column(JSONB, default=list)
    affected_models: Mapped[list] = mapped_column(JSONB, default=list)
    priority: Mapped[str] = mapped_column(String(20), default="important")

    applied: Mapped[bool] = mapped_column(Boolean, default=False)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    applied_to_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("detection_tasks.id", ondelete="SET NULL"), nullable=True
    )

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


# ════════════════════════════════════════════════════════════════
# Multimodal Asset Tracking (实景/视频/音频资产)
# ════════════════════════════════════════════════════════════════

class MultimodalAsset(Base):
    """多模态实景资产 — 独立于知识库的实拍图/视频/音频资产追踪。

    Tracks the enterprise's visual assets that influence model trust:
    - 工厂/厂区实拍图
    - 产品落地照片
    - 短视频/直播内容
    - 线下门店实景
    """

    __tablename__ = "multimodal_assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    asset_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # factory_photo / product_photo / store_photo / video / audio / live_stream

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    file_path: Mapped[str | None] = mapped_column(String(1000))
    file_url: Mapped[str | None] = mapped_column(String(2000))
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    platform: Mapped[str | None] = mapped_column(String(100))
    # e.g., "抖音", "小红书", "视频号", "本地存储"

    geo_tags: Mapped[list] = mapped_column(JSONB, default=list)
    # e.g., [{"address": "...", "lat": ..., "lng": ...}]

    coverage_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100 实景覆盖度

    tags: Mapped[list] = mapped_column(JSONB, default=list)
    extra_meta: Mapped[dict] = mapped_column(JSONB, default=dict)

    status: Mapped[str] = mapped_column(String(20), default="active")  # active/archived
    recorded_at: Mapped[date | None] = mapped_column(Date)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )


# ════════════════════════════════════════════════════════════════
# Comment Q&A Tracking (评论区/问答区内容)
# ════════════════════════════════════════════════════════════════

class CommentQATracking(Base):
    """评论区/问答区内容追踪 — 全网用户评论、问答、口碑数据。

    Tracks the full comment ecosystem to feed sentiment analysis
    and content quality scoring.
    """

    __tablename__ = "comment_qa_tracking"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    platform: Mapped[str] = mapped_column(String(100), nullable=False)
    # e.g., "百度知道", "知乎", "抖音评论", "小红书评论", "1688咨询"

    source_url: Mapped[str | None] = mapped_column(String(2000))
    question: Mapped[str | None] = mapped_column(Text)
    answer: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String(200))

    sentiment: Mapped[str] = mapped_column(String(20), default="neutral")
    # positive / neutral / negative

    keywords_matched: Mapped[list] = mapped_column(JSONB, default=list)
    mentions_company: Mapped[bool] = mapped_column(Boolean, default=False)
    mentions_competitor: Mapped[bool] = mapped_column(Boolean, default=False)
    competitor_name: Mapped[str | None] = mapped_column(String(200))

    engagement_count: Mapped[int] = mapped_column(Integer, default=0)  # 点赞/回复数
    is_verified_answer: Mapped[bool] = mapped_column(Boolean, default=False)
    needs_response: Mapped[bool] = mapped_column(Boolean, default=False)

    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

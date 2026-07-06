"""P3 Industry Template Models — Pre-built solutions for rapid customer onboarding."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from app.core.db_types import UniversalUUID as UUID, UniversalJSON as JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class IndustryTemplate(Base):
    """Pre-built industry solution template for one-click customer setup."""

    __tablename__ = "industry_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    industry: Mapped[str] = mapped_column(String(100), nullable=False)  # manufacturing, local_service, ecommerce, education, healthcare
    description: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str | None] = mapped_column(String(100))  # Icon name for display
    preset_keywords: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # [{word, type: broad|product|comparison|scenario}]
    pain_points: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # 行业痛点词库
    asset_structure: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # [{name, asset_type, content_type, description, example}]
    recommended_channels: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # [{name, channel_type, tier, reason}]
    content_strategy: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # {tone_style, content_types, seo_tips, prompt_templates}
    competitor_suggestions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    use_case: Mapped[str | None] = mapped_column(Text)  # 适用场景说明
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)  # System template or custom
    customer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

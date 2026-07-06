"""P5 Demo detection chat log — persistent storage of Agent1 multi-model Q&A interactions."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Integer, String, Text
from app.core.db_types import UniversalUUID as UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class DemoChatLog(Base):
    """Stores every prompt and model response from Agent1 multi-model probing."""

    __tablename__ = "demo_detect_chat_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    user_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model_reply: Mapped[str] = mapped_column(Text, nullable=False)
    source_urls: Mapped[str | None] = mapped_column(Text)  # JSON list of crawled URLs
    company_name: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    is_rival: Mapped[bool] = mapped_column(default=False)  # True if this is a competitor probe
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

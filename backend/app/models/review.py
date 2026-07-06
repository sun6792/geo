"""Review workflow ORM models — dual-review (internal + client) system."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ReviewRecord(Base):
    """Core review entity. Each draft goes through internal_review → client_review. Both must pass."""

    __tablename__ = "review_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    draft_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("content_drafts.id", ondelete="CASCADE"), nullable=False)
    stage: Mapped[str] = mapped_column(String(30), nullable=False)  # internal_review, client_review
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")  # pending, approved, rejected, changes_requested
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    client_reviewer_email: Mapped[str | None] = mapped_column(String(320))
    client_reviewer_name: Mapped[str | None] = mapped_column(String(200))
    client_access_token: Mapped[str | None] = mapped_column(String(256))
    client_token_expires: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    comments = relationship("ReviewComment", back_populates="review_record", lazy="selectin", cascade="all, delete-orphan")
    approval_chain = relationship("ReviewApprovalChain", back_populates="review_record", lazy="selectin", cascade="all, delete-orphan")
    checklist_results = relationship("ReviewChecklistResult", back_populates="review_record", lazy="selectin", cascade="all, delete-orphan")


class ReviewComment(Base):
    """Individual review comment with threading and inline text selection support."""

    __tablename__ = "review_comments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    review_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("review_records.id", ondelete="CASCADE"), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("review_comments.id", ondelete="CASCADE"))
    comment_text: Mapped[str] = mapped_column(Text, nullable=False)
    comment_type: Mapped[str] = mapped_column(String(30), nullable=False, default="general")
    selection_start: Mapped[int | None] = mapped_column(Integer)
    selection_end: Mapped[int | None] = mapped_column(Integer)
    selected_text: Mapped[str | None] = mapped_column(Text)
    is_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    review_record = relationship("ReviewRecord", back_populates="comments")
    replies = relationship("ReviewComment", backref="parent", remote_side=[id], lazy="selectin")


class ReviewApprovalChain(Base):
    """Approval flow record: who approved/rejected and when."""

    __tablename__ = "review_approval_chain"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    review_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("review_records.id", ondelete="CASCADE"), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # approved, rejected, changes_requested
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)  # internal_user, client
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    actor_email: Mapped[str | None] = mapped_column(String(320))
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    review_record = relationship("ReviewRecord", back_populates="approval_chain")


class ReviewChecklist(Base):
    """Customizable review criteria per customer."""

    __tablename__ = "review_checklists"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    stage: Mapped[str] = mapped_column(String(30), nullable=False)  # internal_review, client_review
    item_text: Mapped[str] = mapped_column(String(500), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ReviewChecklistResult(Base):
    """Per-review checklist item completion tracking."""

    __tablename__ = "review_checklist_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    review_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("review_records.id", ondelete="CASCADE"), nullable=False)
    checklist_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("review_checklists.id", ondelete="CASCADE"), nullable=False)
    is_checked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    checked_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    review_record = relationship("ReviewRecord", back_populates="checklist_results")

"""P5 Customer sub-account and payment record models."""

import uuid
from datetime import datetime, timezone, date

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from app.core.db_types import UniversalUUID as UUID, UniversalJSON as JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class SubAccount(Base):
    """Customer sub-account — read-only portal access for paying customers."""

    __tablename__ = "sub_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(300))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    service_start: Mapped[date] = mapped_column(Date, nullable=False)
    service_end: Mapped[date | None] = mapped_column(Date)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class PaymentRecord(Base):
    """Offline payment record for customer subscriptions."""

    __tablename__ = "payment_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    sub_account_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sub_accounts.id", ondelete="SET NULL"), nullable=True)
    company_name: Mapped[str] = mapped_column(String(300), nullable=False)
    plan_name: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    billing_cycle: Mapped[str] = mapped_column(String(10), nullable=False, default="yearly")
    service_start: Mapped[date] = mapped_column(Date, nullable=False)
    service_end: Mapped[date] = mapped_column(Date, nullable=False)
    payment_method: Mapped[str | None] = mapped_column(String(50))
    payment_ref: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

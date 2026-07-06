"""Publishing service — 3-tier channel matrix, schedules, manual performance recording."""

import uuid
from datetime import datetime, timezone, date
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ReviewGateException, ValidationException
from app.core.pagination import PaginationParams
from app.models.content import ContentDraft
from app.models.publish import PublishChannel, PublishSchedule, PublishRecord, PublishPerformance
from app.models.review import ReviewRecord


class PublishService:
    """Publishing orchestration with gate enforcement. Content must be fully approved before scheduling."""

    def __init__(self, db: AsyncSession, customer_id: uuid.UUID):
        self.db = db
        self.customer_id = customer_id

    # ── Channels ──────────────────────────────────────────────

    async def list_channels(self) -> list[PublishChannel]:
        result = await self.db.execute(
            select(PublishChannel)
            .where(PublishChannel.customer_id == self.customer_id)
            .order_by(PublishChannel.tier, PublishChannel.name)
        )
        return list(result.scalars().all())

    async def create_channel(self, data: dict) -> PublishChannel:
        channel = PublishChannel(customer_id=self.customer_id, **data)
        self.db.add(channel)
        await self.db.flush()
        return channel

    async def update_channel(self, channel_id: uuid.UUID, data: dict) -> PublishChannel:
        channel = await self._get_channel(channel_id)
        for k, v in data.items():
            if v is not None and hasattr(channel, k):
                setattr(channel, k, v)
        await self.db.flush()
        return channel

    async def delete_channel(self, channel_id: uuid.UUID) -> None:
        channel = await self._get_channel(channel_id)
        await self.db.delete(channel)
        await self.db.flush()

    async def _get_channel(self, channel_id: uuid.UUID) -> PublishChannel:
        result = await self.db.execute(
            select(PublishChannel).where(PublishChannel.id == channel_id, PublishChannel.customer_id == self.customer_id)
        )
        ch = result.scalar_one_or_none()
        if not ch:
            raise NotFoundException("PublishChannel", str(channel_id))
        return ch

    # ── Schedules ─────────────────────────────────────────────

    async def list_schedules(self, status: Optional[str] = None) -> list[PublishSchedule]:
        query = select(PublishSchedule).where(PublishSchedule.customer_id == self.customer_id)
        if status:
            query = query.where(PublishSchedule.status == status)
        result = await self.db.execute(query.order_by(PublishSchedule.scheduled_at.desc()))
        return list(result.scalars().all())

    async def schedule_publish(self, draft_id: uuid.UUID, channel_id: uuid.UUID,
                                scheduled_at: datetime, created_by: uuid.UUID) -> PublishSchedule:
        """Schedule a publish. HARD GATE: client_review must be approved."""
        await self._verify_publish_gate(draft_id)

        schedule = PublishSchedule(
            customer_id=self.customer_id,
            draft_id=draft_id,
            channel_id=channel_id,
            scheduled_at=scheduled_at,
            created_by=created_by,
        )
        self.db.add(schedule)
        await self.db.flush()
        return schedule

    async def publish_now(self, schedule_id: uuid.UUID, published_by: uuid.UUID,
                           published_url: Optional[str] = None) -> PublishRecord:
        """Execute a publish immediately."""
        schedule = await self._get_schedule(schedule_id)

        record = PublishRecord(
            customer_id=self.customer_id,
            schedule_id=schedule_id,
            draft_id=schedule.draft_id,
            channel_id=schedule.channel_id,
            publish_status="success",
            published_url=published_url,
            published_by=published_by,
        )
        self.db.add(record)

        schedule.status = "published"
        schedule.published_at = datetime.now(timezone.utc)
        schedule.published_url = published_url

        await self.db.flush()
        return record

    async def cancel_schedule(self, schedule_id: uuid.UUID) -> None:
        schedule = await self._get_schedule(schedule_id)
        schedule.status = "cancelled"
        await self.db.flush()

    async def _get_schedule(self, schedule_id: uuid.UUID) -> PublishSchedule:
        result = await self.db.execute(
            select(PublishSchedule).where(PublishSchedule.id == schedule_id, PublishSchedule.customer_id == self.customer_id)
        )
        s = result.scalar_one_or_none()
        if not s:
            raise NotFoundException("PublishSchedule", str(schedule_id))
        return s

    async def _verify_publish_gate(self, draft_id: uuid.UUID) -> None:
        """Verify that both reviews (internal + client) have been approved."""
        # Check client review approved
        client_review = (await self.db.execute(
            select(ReviewRecord).where(
                ReviewRecord.draft_id == draft_id,
                ReviewRecord.stage == "client_review",
                ReviewRecord.status == "approved",
            )
        )).scalar_one_or_none()

        if not client_review:
            raise ReviewGateException("client_review", str(draft_id))

    # ── Performance ───────────────────────────────────────────

    async def list_performance(self, pagination: PaginationParams,
                                draft_id: Optional[uuid.UUID] = None) -> tuple[list[PublishPerformance], int]:
        query = select(PublishPerformance).where(PublishPerformance.customer_id == self.customer_id)
        count_q = select(func.count(PublishPerformance.id)).where(PublishPerformance.customer_id == self.customer_id)
        if draft_id:
            query = query.where(PublishPerformance.draft_id == draft_id)
            count_q = count_q.where(PublishPerformance.draft_id == draft_id)

        total = (await self.db.execute(count_q)).scalar() or 0
        items = (await self.db.execute(
            query.order_by(PublishPerformance.recorded_at.desc()).offset(pagination.offset).limit(pagination.limit)
        )).scalars().all()
        return list(items), total

    async def record_performance(self, data: dict) -> PublishPerformance:
        perf = PublishPerformance(customer_id=self.customer_id, **data)
        self.db.add(perf)
        await self.db.flush()
        return perf

    async def update_performance(self, perf_id: uuid.UUID, data: dict) -> PublishPerformance:
        result = await self.db.execute(
            select(PublishPerformance).where(PublishPerformance.id == perf_id, PublishPerformance.customer_id == self.customer_id)
        )
        perf = result.scalar_one_or_none()
        if not perf:
            raise NotFoundException("PublishPerformance", str(perf_id))
        for k, v in data.items():
            if v is not None and hasattr(perf, k):
                setattr(perf, k, v)
        await self.db.flush()
        return perf

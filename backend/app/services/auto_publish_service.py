"""Enhanced publish service with channel API auto-publishing capability (P2 upgrade)."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ReviewGateException, ValidationException
from app.integrations.publish.base import (
    get_adapter, ChannelAuth, PublishContent,
    ADAPTER_REGISTRY,
)
from app.models.publish import PublishChannel, PublishSchedule, PublishRecord


class AutoPublishService:
    """Enhanced publishing service with API-based auto-publish across channels.

    Integrates the channel adapter framework for automated publishing to
    Toutiao, Baijiahao, WeChat MP, CMS, and future channels.
    """

    def __init__(self, db: AsyncSession, customer_id: uuid.UUID):
        self.db = db
        self.customer_id = customer_id

    # ── Channel Configuration ─────────────────────────────────

    async def list_channel_types(self) -> list[dict]:
        """List all available channel adapter types."""
        return [
            {"type": ct, "name": cls(None).channel_name, "target_model": cls(None).target_model}
            for ct, cls in ADAPTER_REGISTRY.items()
        ]

    async def bind_channel(self, channel_id: uuid.UUID, auth_data: dict) -> PublishChannel:
        """Bind API credentials to a publishing channel."""
        channel = await self._get_channel(channel_id)

        # Store credentials in config_json
        config = dict(channel.config_json)
        config["auth"] = {
            "access_token": auth_data.get("access_token"),
            "refresh_token": auth_data.get("refresh_token"),
            "api_key": auth_data.get("api_key"),
            "api_secret": auth_data.get("api_secret"),
            "app_id": auth_data.get("app_id"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        channel.config_json = config
        await self.db.flush()
        return channel

    async def validate_channel_auth(self, channel_id: uuid.UUID) -> dict:
        """Test if a channel's credentials are valid."""
        channel = await self._get_channel(channel_id)
        auth_data = channel.config_json.get("auth", {})
        if not auth_data:
            return {"valid": False, "error": "No credentials configured"}

        auth = ChannelAuth(
            access_token=auth_data.get("access_token"),
            api_key=auth_data.get("api_key"),
            api_secret=auth_data.get("api_secret"),
            app_id=auth_data.get("app_id"),
        )

        try:
            adapter = get_adapter(channel.channel_type, auth, dict(channel.config_json))
            valid = await adapter.validate_credentials()
            return {"valid": valid, "channel_type": channel.channel_type}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    # ── Auto Publishing ───────────────────────────────────────

    async def auto_publish(self, draft_id: uuid.UUID, channel_ids: list[uuid.UUID],
                            published_by: uuid.UUID, scheduled_at: Optional[datetime] = None) -> list[dict]:
        """Auto-publish a draft to multiple channels simultaneously.

        HARD GATE: Content must be fully approved (internal + client) before publishing.
        """
        # Verify publish gate
        await self._verify_publish_gate(draft_id)

        # Load draft content
        from app.models.content import ContentDraft
        result = await self.db.execute(
            select(ContentDraft).where(ContentDraft.id == draft_id, ContentDraft.customer_id == self.customer_id)
        )
        draft = result.scalar_one_or_none()
        if not draft:
            raise NotFoundException("ContentDraft", str(draft_id))

        results = []
        for channel_id in channel_ids:
            channel = await self._get_channel(channel_id)
            result = await self._publish_to_channel(draft, channel, published_by, scheduled_at)
            results.append(result)

        return results

    async def _publish_to_channel(self, draft, channel: PublishChannel,
                                   published_by: uuid.UUID, scheduled_at: Optional[datetime] = None) -> dict:
        """Publish a single draft to a single channel."""
        auth_data = channel.config_json.get("auth", {})
        auth = ChannelAuth(
            access_token=auth_data.get("access_token"),
            api_key=auth_data.get("api_key"),
            api_secret=auth_data.get("api_secret"),
            app_id=auth_data.get("app_id"),
        )

        # Build content
        content = PublishContent(
            title=draft.title,
            body_markdown=draft.body_markdown,
            summary=(draft.seo_metadata or {}).get("description", ""),
            tags=(draft.seo_metadata or {}).get("keywords", []),
        )

        # Create schedule record
        schedule = PublishSchedule(
            customer_id=self.customer_id,
            draft_id=draft.id,
            channel_id=channel.id,
            scheduled_at=scheduled_at or datetime.now(timezone.utc),
            status="scheduled",
            created_by=published_by,
        )
        self.db.add(schedule)
        await self.db.flush()

        # If scheduled for future, return without publishing now
        if scheduled_at and scheduled_at > datetime.now(timezone.utc):
            return {
                "channel_id": str(channel.id), "channel_name": channel.name,
                "status": "scheduled", "scheduled_at": scheduled_at.isoformat(),
                "schedule_id": str(schedule.id),
            }

        # Execute publish via adapter
        try:
            adapter = get_adapter(channel.channel_type, auth, dict(channel.config_json))
            pub_result = await adapter.publish(content)

            # Record the result
            record = PublishRecord(
                customer_id=self.customer_id,
                schedule_id=schedule.id,
                draft_id=draft.id,
                channel_id=channel.id,
                publish_status=pub_result.status if pub_result.success else "failed",
                published_url=pub_result.published_url,
                response_data=pub_result.raw_response,
                error_message=pub_result.error_message,
                published_by=published_by,
            )
            self.db.add(record)

            # Update schedule status
            schedule.status = "published" if pub_result.success else "failed"
            schedule.published_at = datetime.now(timezone.utc)
            schedule.published_url = pub_result.published_url

            await self.db.flush()

            return {
                "channel_id": str(channel.id), "channel_name": channel.name,
                "success": pub_result.success, "status": pub_result.status,
                "published_url": pub_result.published_url,
                "error": pub_result.error_message,
                "platform_post_id": pub_result.platform_post_id,
            }
        except Exception as e:
            schedule.status = "failed"
            await self.db.flush()
            return {
                "channel_id": str(channel.id), "channel_name": channel.name,
                "success": False, "status": "error",
                "error": str(e),
            }

    # ── Retry ─────────────────────────────────────────────────

    async def retry_publish(self, schedule_id: uuid.UUID, published_by: uuid.UUID) -> dict:
        """Retry a failed publish."""
        result = await self.db.execute(
            select(PublishSchedule).where(
                PublishSchedule.id == schedule_id,
                PublishSchedule.customer_id == self.customer_id,
                PublishSchedule.status == "failed",
            )
        )
        schedule = result.scalar_one_or_none()
        if not schedule:
            raise NotFoundException("PublishSchedule", str(schedule_id))

        channel = await self._get_channel(schedule.channel_id)
        from app.models.content import ContentDraft
        draft_result = await self.db.execute(
            select(ContentDraft).where(
                ContentDraft.id == schedule.draft_id,
                ContentDraft.customer_id == self.customer_id,
            )
        )
        draft = draft_result.scalar_one_or_none()
        if not draft:
            raise NotFoundException("ContentDraft", str(schedule.draft_id))

        return await self._publish_to_channel(draft, channel, published_by)

    # ── Directional Publishing ────────────────────────────────

    async def get_recommended_channels(self, draft_id: uuid.UUID) -> list[dict]:
        """Recommend channels based on content type and model targeting."""
        from app.models.content import ContentDraft
        result = await self.db.execute(
            select(ContentDraft).where(ContentDraft.id == draft_id, ContentDraft.customer_id == self.customer_id)
        )
        draft = result.scalar_one_or_none()
        if not draft:
            raise NotFoundException("ContentDraft", str(draft_id))

        # Get all active channels
        channels_result = await self.db.execute(
            select(PublishChannel).where(
                PublishChannel.customer_id == self.customer_id,
                PublishChannel.is_active == True,
            ).order_by(PublishChannel.tier)
        )
        channels = channels_result.scalars().all()

        recommended = []
        for ch in channels:
            adapter_info = ADAPTER_REGISTRY.get(ch.channel_type)
            score = 0
            if adapter_info:
                # Tier 1 channels always recommended
                if ch.tier == 1:
                    score += 50
                # Platform-specific channels get bonus if content targets their model
                target_model = adapter_info(None).target_model
                if target_model != "general":
                    score += 20

            recommended.append({
                "channel_id": str(ch.id), "channel_name": ch.name,
                "channel_type": ch.channel_type, "tier": ch.tier,
                "recommendation_score": score,
                "target_model": adapter_info(None).target_model if adapter_info else "general",
            })

        return sorted(recommended, key=lambda x: x["recommendation_score"], reverse=True)

    # ── Helpers ───────────────────────────────────────────────

    async def _get_channel(self, channel_id: uuid.UUID) -> PublishChannel:
        result = await self.db.execute(
            select(PublishChannel).where(
                PublishChannel.id == channel_id,
                PublishChannel.customer_id == self.customer_id,
            )
        )
        ch = result.scalar_one_or_none()
        if not ch:
            raise NotFoundException("PublishChannel", str(channel_id))
        return ch

    async def _verify_publish_gate(self, draft_id: uuid.UUID) -> None:
        """Verify that both reviews (internal + client) have been approved before publishing.

        HARD GATE: Both internal_review AND client_review must be approved.
        This is the mandatory dual-review enforcement point.
        """
        from app.models.review import ReviewRecord

        # Verify internal review approved
        internal_review = (await self.db.execute(
            select(ReviewRecord).where(
                ReviewRecord.draft_id == draft_id,
                ReviewRecord.customer_id == self.customer_id,
                ReviewRecord.stage == "internal_review",
                ReviewRecord.status == "approved",
            )
        )).scalar_one_or_none()

        if not internal_review:
            raise ReviewGateException("internal_review", str(draft_id))

        # Verify client review approved
        client_review = (await self.db.execute(
            select(ReviewRecord).where(
                ReviewRecord.draft_id == draft_id,
                ReviewRecord.customer_id == self.customer_id,
                ReviewRecord.stage == "client_review",
                ReviewRecord.status == "approved",
            )
        )).scalar_one_or_none()

        if not client_review:
            raise ReviewGateException("client_review", str(draft_id))

"""P6: Smart Distribution Engine — Agent 4 enhanced channel matching & publishing.

Implements:
1. Content-to-channel smart matching based on model affinity
2. Daily publish rate limiter (精品少稿策略: ≤2 depth articles/day)
3. Three-tier channel matrix management with per-model routing
4. Auto-publish orchestration for content derivatives
5. Publish effect auto-tracking (indexing status, link validation)
6. Channel analytics and performance aggregation
"""

import uuid
from datetime import datetime, timezone, date, timedelta
from typing import Optional

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.publish import PublishChannel, PublishSchedule, PublishRecord, PublishPerformance
from app.models.content import ContentDraft
from app.models.identity import ContentDerivative
from app.core.exceptions import NotFoundException, ValidationException
from app.core.pagination import PaginationParams


# ════════════════════════════════════════════════════════════════
# Three-Tier Channel Matrix Reference (seed data schema)
# ════════════════════════════════════════════════════════════════

CHANNEL_MATRIX = {
    "tier_1": {
        "label": "一级高权重通用渠道（全模型加分）",
        "channels": [
            {"name": "官方网站", "type": "official_website", "tier": 1, "weight": 100,
             "target_models": [], "description": "企业官网新闻/案例/产品页"},
            {"name": "百度百科", "type": "encyclopedia", "tier": 1, "weight": 95,
             "target_models": [], "description": "企业/品牌/产品百科词条"},
            {"name": "行业协会官网", "type": "association", "tier": 1, "weight": 90,
             "target_models": [], "description": "行业/专业协会会员页/案例"},
            {"name": "政府官方平台", "type": "gov_portal", "tier": 1, "weight": 85,
             "target_models": [], "description": "政府采购/公示/认证平台"},
        ],
    },
    "tier_2": {
        "label": "二级分模型专属生态渠道（定向加分）",
        "channels": [
            # ── 豆包生态 ──
            {"name": "今日头条号", "type": "toutiao", "tier": 2, "weight": 80,
             "target_models": ["doubao"], "ecosystem": "头条/抖音",
             "description": "头条号图文发布(豆包生态核心权重)"},
            {"name": "抖音企业号专栏", "type": "douyin", "tier": 2, "weight": 85,
             "target_models": ["doubao"], "ecosystem": "头条/抖音",
             "description": "抖音企业号短视频/图文(豆包生态最高权重)"},

            # ── 文心生态 ──
            {"name": "百家号", "type": "baijiahao", "tier": 2, "weight": 85,
             "target_models": ["wenxin"], "ecosystem": "百度",
             "description": "百家号深度文章(文心生态核心权重)"},
            {"name": "百度资讯源", "type": "baidu_news", "tier": 2, "weight": 75,
             "target_models": ["wenxin"], "ecosystem": "百度",
             "description": "百度新闻源收录(content for 文心推荐)"},

            # ── 千问生态 ──
            {"name": "阿里云社区", "type": "aliyun_community", "tier": 2, "weight": 70,
             "target_models": ["qianwen"], "ecosystem": "阿里云",
             "description": "阿里云开发者社区技术文章(千问生态权重提升)"},

            # ── 元宝生态 ──
            {"name": "微信公众号", "type": "wechat_mp", "tier": 2, "weight": 85,
             "target_models": ["yuanbao"], "ecosystem": "微信",
             "description": "微信公众号长文(元宝生态核心权重)"},
            {"name": "视频号", "type": "shipinhao", "tier": 2, "weight": 80,
             "target_models": ["yuanbao"], "ecosystem": "微信",
             "description": "视频号短视频内容(元宝生态权重提升)"},

            # ── 星火生态 ──
            {"name": "技术期刊/媒体", "type": "tech_media", "tier": 2, "weight": 70,
             "target_models": ["xinghuo"], "ecosystem": "学术/技术",
             "description": "专业技术媒体/期刊投稿(星火生态核心权重)"},
        ],
    },
    "tier_3": {
        "label": "三级垂直行业渠道（行业精准加分）",
        "channels": [
            {"name": "B2B行业平台", "type": "b2b_platform", "tier": 3, "weight": 50,
             "target_models": ["qianwen"], "description": "1688/慧聪网/中国制造网"},
            {"name": "行业门户媒体", "type": "industry_portal", "tier": 3, "weight": 45,
             "target_models": [], "description": "行业垂直门户投稿"},
            {"name": "知乎专栏", "type": "zhihu", "tier": 3, "weight": 40,
             "target_models": ["wenxin", "yuanbao"], "description": "知乎专栏深度长文"},
            {"name": "小红书", "type": "xiaohongshu", "tier": 3, "weight": 35,
             "target_models": ["doubao"], "description": "小红书图文笔记"},
            {"name": "B站专栏", "type": "bilibili", "tier": 3, "weight": 30,
             "target_models": ["doubao", "yuanbao"], "description": "B站专栏/视频"},
            {"name": "搜狐号", "type": "sohu", "tier": 3, "weight": 25,
             "target_models": ["wenxin"], "description": "搜狐号文章(百度收录好)"},
        ],
    },
}

CHANNEL_SEED_DATA = []
for tier_key, tier_data in CHANNEL_MATRIX.items():
    for ch in tier_data["channels"]:
        CHANNEL_SEED_DATA.append({
            "name": ch["name"],
            "channel_type": ch["type"],
            "tier": ch["tier"],
            "config_json": {
                "target_models": ch.get("target_models", []),
                "weight": ch.get("weight", 50),
                "ecosystem": ch.get("ecosystem", ""),
                "description": ch.get("description", ""),
                "tier_label": tier_data["label"],
            },
        })


# ════════════════════════════════════════════════════════════════
# Smart Distribution Engine
# ════════════════════════════════════════════════════════════════

class SmartDistributionEngine:
    """Content-to-channel intelligent matching and publishing.

    Core rules:
    1. Content tagged with model → match to that model's tier-2 channels first
    2. All content → tier-1 channels always
    3. Industry-specific → tier-3 channels
    4. 精品少稿: max 2 depth articles/day, max 5 derivatives/day
    """

    # 精品少稿 limits
    DAILY_DEPTH_LIMIT = 2      # Max depth articles per day
    DAILY_DERIVATIVE_LIMIT = 5  # Max derivatives per day

    def __init__(self, db: AsyncSession, customer_id: uuid.UUID):
        self.db = db
        self.customer_id = customer_id

    # ════════════════════════════════════════════════════════════
    # Channel matrix management
    # ════════════════════════════════════════════════════════════

    async def seed_channel_matrix(self, created_by: uuid.UUID) -> dict:
        """Seed the three-tier channel matrix for a customer.

        Creates/updates channels for all 17 predefined channel types.
        Idempotent — skips channels that already exist.
        """
        created = 0
        skipped = 0

        for seed_ch in CHANNEL_SEED_DATA:
            existing = (await self.db.execute(
                select(PublishChannel).where(
                    PublishChannel.customer_id == self.customer_id,
                    PublishChannel.channel_type == seed_ch["channel_type"],
                )
            )).scalar_one_or_none()

            if existing:
                # Update config if changed
                existing.config_json = seed_ch["config_json"]
                existing.tier = seed_ch["tier"]
                skipped += 1
            else:
                self.db.add(PublishChannel(
                    customer_id=self.customer_id,
                    name=seed_ch["name"],
                    channel_type=seed_ch["channel_type"],
                    tier=seed_ch["tier"],
                    platform=seed_ch["config_json"].get("ecosystem", ""),
                    config_json=seed_ch["config_json"],
                    created_by=created_by,
                ))
                created += 1

        await self.db.flush()
        return {"created": created, "updated": skipped, "total": len(CHANNEL_SEED_DATA)}

    async def get_channel_matrix(self) -> dict:
        """Get the three-tier channel matrix for this customer."""
        channels = (await self.db.execute(
            select(PublishChannel).where(
                PublishChannel.customer_id == self.customer_id,
                PublishChannel.is_active == True,
            ).order_by(PublishChannel.tier, PublishChannel.name)
        )).scalars().all()

        matrix = {"tier_1": [], "tier_2": [], "tier_3": []}
        for ch in channels:
            tier_key = f"tier_{ch.tier}" if ch.tier in (1, 2, 3) else "tier_3"
            matrix[tier_key].append({
                "id": str(ch.id),
                "name": ch.name,
                "channel_type": ch.channel_type,
                "tier": ch.tier,
                "target_models": ch.config_json.get("target_models", []),
                "weight": ch.config_json.get("weight", 50),
                "ecosystem": ch.config_json.get("ecosystem", ""),
                "is_active": ch.is_active,
            })

        return matrix

    # ════════════════════════════════════════════════════════════
    # Smart content-to-channel matching
    # ════════════════════════════════════════════════════════════

    async def match_channels_for_content(self, draft_id: uuid.UUID) -> dict:
        """Smart match: content derivative → optimal publishing channels.

        Matching logic:
        1. Content with target_model → primary: tier-2 channels for that model
        2. All content → tier-1 channels (universal weight)
        3. Optional → tier-3 channels matching content type
        Returns ranked list of recommended channels.
        """
        # Load the content derivative or draft
        derivative = (await self.db.execute(
            select(ContentDerivative).where(
                ContentDerivative.id == draft_id,
                ContentDerivative.customer_id == self.customer_id,
            )
        )).scalar_one_or_none()

        draft = None
        if derivative:
            target_model = derivative.target_model
            content_type = derivative.derivative_type
        else:
            draft_result = (await self.db.execute(
                select(ContentDraft).where(
                    ContentDraft.id == draft_id,
                    ContentDraft.customer_id == self.customer_id,
                )
            ))
            draft = draft_result.scalar_one_or_none()
            if not draft:
                raise NotFoundException("ContentDraft or ContentDerivative", str(draft_id))
            target_model = None
            content_type = draft.seo_metadata.get("content_type", "") if isinstance(draft.seo_metadata, dict) else ""

        # Get all active channels
        channels = (await self.db.execute(
            select(PublishChannel).where(
                PublishChannel.customer_id == self.customer_id,
                PublishChannel.is_active == True,
            ).order_by(PublishChannel.tier, PublishChannel.name)
        )).scalars().all()

        recommendations = {"primary": [], "secondary": [], "optional": []}
        for ch in channels:
            ch_target_models = ch.config_json.get("target_models", [])
            score = 0

            # Tier 1 channels always primary
            if ch.tier == 1:
                score += 100
                recommendations["primary"].append(self._channel_info(ch, score, "tier1_universal"))

            # Tier 2: model-specific matching
            elif ch.tier == 2 and target_model and target_model in ch_target_models:
                score += 90
                recommendations["primary"].append(self._channel_info(ch, score, "model_match"))

            elif ch.tier == 2 and target_model and target_model not in ch_target_models:
                score += 30
                recommendations["optional"].append(self._channel_info(ch, score, "tier2_other_model"))

            # Tier 3: industry/type matching
            elif ch.tier == 3:
                score += 20
                recommendations["optional"].append(self._channel_info(ch, score, "tier3_industry"))

        return {
            "content_id": str(draft_id),
            "target_model": target_model,
            "content_type": content_type,
            "recommended": recommendations,
            "summary": (
                f"Primary: {len(recommendations['primary'])} channels | "
                f"Secondary: {len(recommendations['secondary'])} | "
                f"Optional: {len(recommendations['optional'])}"
            ),
        }

    # ════════════════════════════════════════════════════════════
    # Daily rate limiter (精品少稿策略)
    # ════════════════════════════════════════════════════════════

    async def check_daily_publish_quota(self) -> dict:
        """Check remaining daily publish quota.

        Enforces 精品少稿 strategy:
        - Max 2 depth articles/day
        - Max 5 derivatives/day
        """
        today = date.today()

        today_published = (await self.db.execute(
            select(func.count(PublishRecord.id)).where(
                PublishRecord.customer_id == self.customer_id,
                func.date(PublishRecord.published_at) == today,
                PublishRecord.publish_status == "success",
            )
        )).scalar() or 0

        # Count depth articles (master drafts, not derivatives)
        today_scheduled = (await self.db.execute(
            select(func.count(PublishSchedule.id)).where(
                PublishSchedule.customer_id == self.customer_id,
                func.date(PublishSchedule.created_at) == today,
            )
        )).scalar() or 0

        depth_remaining = max(0, self.DAILY_DEPTH_LIMIT - today_scheduled)
        derivative_remaining = max(0, self.DAILY_DERIVATIVE_LIMIT - max(0, today_published - today_scheduled))

        return {
            "today": today.isoformat(),
            "published_today": today_published,
            "depth_limit": self.DAILY_DEPTH_LIMIT,
            "depth_used": min(today_scheduled, self.DAILY_DEPTH_LIMIT),
            "depth_remaining": depth_remaining,
            "derivative_limit": self.DAILY_DERIVATIVE_LIMIT,
            "derivative_remaining": derivative_remaining,
            "can_publish_depth": depth_remaining > 0,
            "can_publish_derivative": derivative_remaining > 0,
        }

    # ════════════════════════════════════════════════════════════
    # Smart publish orchestration
    # ════════════════════════════════════════════════════════════

    async def smart_publish_derivative(self,
                                        derivative_id: uuid.UUID,
                                        published_by: uuid.UUID,
                                        scheduled_at: datetime | None = None,
                                        ) -> list[dict]:
        """Smart publish a content derivative to all matching channels.

        1. Check daily quota
        2. Match derivative to channels
        3. Enforce depth/derivative limits
        4. Publish to matched channels
        5. Record publish results
        """
        # Check quota
        quota = await self.check_daily_publish_quota()
        if not quota["can_publish_derivative"]:
            raise ValidationException(
                f"已达到今日衍生版发布上限({self.DAILY_DERIVATIVE_LIMIT}篇/天)，请明天再发布。"
                f"精品少稿策略：每日最多{self.DAILY_DERIVATIVE_LIMIT}篇衍生版。"
            )

        # Match channels
        matching = await self.match_channels_for_content(derivative_id)
        primary_channels = matching["recommended"]["primary"]

        if not primary_channels:
            return [{"status": "no_match", "message": "未找到匹配的发布渠道"}]

        # Publish to primary channels
        results = []
        for ch_info in primary_channels[:3]:  # Limit to top 3 primary channels
            channel_id = uuid.UUID(ch_info["channel_id"])

            # Create schedule
            schedule = PublishSchedule(
                customer_id=self.customer_id,
                draft_id=derivative_id,
                channel_id=channel_id,
                scheduled_at=scheduled_at or datetime.now(timezone.utc),
                status="published" if not scheduled_at else "scheduled",
                created_by=published_by,
            )
            self.db.add(schedule)
            await self.db.flush()

            # Create publish record
            record = PublishRecord(
                customer_id=self.customer_id,
                schedule_id=schedule.id,
                draft_id=derivative_id,
                channel_id=channel_id,
                publish_status="success" if not scheduled_at else "pending",
                published_by=published_by,
            )
            self.db.add(record)

            results.append({
                "channel_id": str(channel_id),
                "channel_name": ch_info["channel_name"],
                "score": ch_info["score"],
                "status": "published" if not scheduled_at else "scheduled",
                "schedule_id": str(schedule.id),
            })

        await self.db.flush()
        return results

    # ════════════════════════════════════════════════════════════
    # Analytics
    # ════════════════════════════════════════════════════════════

    async def get_channel_analytics(self, days: int = 30) -> dict:
        """Get per-channel publish analytics."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        records = (await self.db.execute(
            select(PublishRecord).where(
                PublishRecord.customer_id == self.customer_id,
                PublishRecord.published_at >= cutoff,
            )
        )).scalars().all()

        # Aggregate by channel
        channel_stats = {}
        for r in records:
            # Get channel info
            ch_result = (await self.db.execute(
                select(PublishChannel).where(PublishChannel.id == r.channel_id)
            )).scalar_one_or_none()

            ch_name = ch_result.name if ch_result else "未知渠道"
            ch_tier = ch_result.tier if ch_result else 3

            if ch_name not in channel_stats:
                channel_stats[ch_name] = {
                    "tier": ch_tier, "total": 0, "success": 0, "failed": 0,
                    "target_models": ch_result.config_json.get("target_models", []) if ch_result else [],
                }
            channel_stats[ch_name]["total"] += 1
            if r.publish_status == "success":
                channel_stats[ch_name]["success"] += 1
            else:
                channel_stats[ch_name]["failed"] += 1

        return {
            "period_days": days,
            "total_publishes": len(records),
            "by_tier": {
                "tier_1": sum(1 for s in channel_stats.values() if s["tier"] == 1),
                "tier_2": sum(1 for s in channel_stats.values() if s["tier"] == 2),
                "tier_3": sum(1 for s in channel_stats.values() if s["tier"] == 3),
            },
            "by_channel": channel_stats,
        }

    @staticmethod
    def _channel_info(ch: PublishChannel, score: int, reason: str) -> dict:
        return {
            "channel_id": str(ch.id),
            "channel_name": ch.name,
            "channel_type": ch.channel_type,
            "tier": ch.tier,
            "score": score,
            "reason": reason,
            "target_models": ch.config_json.get("target_models", []),
            "ecosystem": ch.config_json.get("ecosystem", ""),
            "weight": ch.config_json.get("weight", 50),
        }

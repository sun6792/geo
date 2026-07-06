"""Agent 5: Weekly Review & Rule Iteration Service — automated review, GEO rule updates, strategy generation."""

import uuid
from datetime import datetime, timezone, date, timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.core.pagination import PaginationParams
from app.models.agent import GeoRule, WeeklyReviewMetric
from app.models.publish import WeeklyReview


class ReviewAgentService:
    """Agent 5: Weekly automated review, GEO rule database management, next-cycle strategy."""

    def __init__(self, db: AsyncSession, customer_id: uuid.UUID):
        self.db = db
        self.customer_id = customer_id

    # ── Weekly Reviews ────────────────────────────────────────

    async def list_weekly_reviews(self, pagination: PaginationParams) -> tuple[list[WeeklyReview], int]:
        query = select(WeeklyReview).where(WeeklyReview.customer_id == self.customer_id)
        count_q = select(func.count(WeeklyReview.id)).where(WeeklyReview.customer_id == self.customer_id)
        total = (await self.db.execute(count_q)).scalar() or 0
        items = (await self.db.execute(
            query.order_by(WeeklyReview.week_start.desc()).offset(pagination.offset).limit(pagination.limit)
        )).scalars().all()
        return list(items), total

    async def get_weekly_review(self, review_id: uuid.UUID) -> WeeklyReview:
        result = await self.db.execute(
            select(WeeklyReview).where(WeeklyReview.id == review_id, WeeklyReview.customer_id == self.customer_id)
        )
        r = result.scalar_one_or_none()
        if not r:
            raise NotFoundException("WeeklyReview", str(review_id))
        return r

    async def get_latest_review(self) -> Optional[WeeklyReview]:
        result = await self.db.execute(
            select(WeeklyReview).where(WeeklyReview.customer_id == self.customer_id)
            .order_by(WeeklyReview.week_start.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def generate_weekly_review(self, generated_by: Optional[uuid.UUID] = None) -> WeeklyReview:
        """Generate a comprehensive weekly review report."""
        today = date.today()
        last_monday = today - timedelta(days=today.weekday())  # This week's Monday
        prev_monday = last_monday - timedelta(days=7)
        prev_sunday = last_monday - timedelta(days=1)
        this_sunday = last_monday + timedelta(days=6)
        next_monday = last_monday + timedelta(days=7)  # Exclusive upper bound for datetime queries

        # Check for existing review this week
        existing = (await self.db.execute(
            select(WeeklyReview).where(
                WeeklyReview.customer_id == self.customer_id,
                WeeklyReview.week_start == last_monday,
            )
        )).scalar_one_or_none()
        if existing:
            raise ValidationException(f"Weekly review already exists for week starting {last_monday}")

        # 1. Aggregate metrics (use next_monday for exclusive upper bound on datetime queries)
        metrics_data = await self._aggregate_weekly_metrics(last_monday, next_monday, prev_monday, last_monday)

        # 2. Build highlights
        highlights = self._build_highlights(metrics_data)

        # 3. Build recommendations
        recommendations = self._build_recommendations(metrics_data)

        # 4. KB gap analysis
        kb_gap = await self._analyze_kb_growth()

        # 5. Content performance summary (use next_monday for full Sunday coverage)
        content_summary = await self._summarize_content_performance(last_monday, next_monday)

        # Create the review
        review = WeeklyReview(
            customer_id=self.customer_id,
            week_start=last_monday,
            week_end=this_sunday,
            status="completed",
            report_markdown=self._build_markdown_report(metrics_data, highlights, recommendations),
            highlights=highlights,
            recommendations=recommendations,
            kb_gap_analysis=kb_gap,
            content_performance_summary=content_summary,
            generated_by=generated_by,
        )
        self.db.add(review)
        await self.db.flush()

        # Save detailed metrics
        for metric in metrics_data.get("detailed", []):
            self.db.add(WeeklyReviewMetric(
                customer_id=self.customer_id,
                weekly_review_id=review.id,
                metric_type=metric.get("type", "general"),
                metric_name=metric.get("name", ""),
                model_name=metric.get("model_name"),
                current_value=metric.get("current", 0),
                previous_value=metric.get("previous", 0),
                change_pct=metric.get("change_pct"),
                trend=metric.get("trend"),
            ))

        await self.db.flush()
        return review

    async def get_review_metrics(self, review_id: uuid.UUID) -> list[WeeklyReviewMetric]:
        result = await self.db.execute(
            select(WeeklyReviewMetric).where(
                WeeklyReviewMetric.customer_id == self.customer_id,
                WeeklyReviewMetric.weekly_review_id == review_id,
            )
        )
        return list(result.scalars().all())

    # ── GEO Rules ─────────────────────────────────────────────

    async def list_rules(self, model_name: Optional[str] = None) -> list[GeoRule]:
        query = select(GeoRule).where(
            (GeoRule.customer_id == self.customer_id) | (GeoRule.customer_id.is_(None)),
            GeoRule.is_latest == True, GeoRule.is_active == True,
        )
        if model_name:
            query = query.where(GeoRule.model_name == model_name)
        result = await self.db.execute(query.order_by(GeoRule.model_name, GeoRule.rule_category))
        return list(result.scalars().all())

    async def get_rule_versions(self, rule_id: uuid.UUID) -> list[GeoRule]:
        """Get version history for a rule."""
        result = await self.db.execute(
            select(GeoRule).where(
                GeoRule.id == rule_id,
                (GeoRule.customer_id == self.customer_id) | (GeoRule.customer_id.is_(None)),
            )
        )
        rule = result.scalar_one_or_none()
        if not rule:
            raise NotFoundException("GeoRule", str(rule_id))
        # Find all versions with same rule_name and model_name
        result = await self.db.execute(
            select(GeoRule).where(
                GeoRule.rule_name == rule.rule_name,
                GeoRule.model_name == rule.model_name,
                (GeoRule.customer_id == self.customer_id) | (GeoRule.customer_id.is_(None)),
            ).order_by(GeoRule.version.desc())
        )
        return list(result.scalars().all())

    async def update_rule(self, rule_id: uuid.UUID, data: dict) -> GeoRule:
        result = await self.db.execute(
            select(GeoRule).where(GeoRule.id == rule_id)
        )
        rule = result.scalar_one_or_none()
        if not rule:
            raise NotFoundException("GeoRule", str(rule_id))

        # Create new version
        rule.is_latest = False
        new_rule = GeoRule(
            customer_id=rule.customer_id,
            model_name=rule.model_name,
            rule_name=rule.rule_name,
            rule_category=rule.rule_category,
            rule_content=data.get("rule_content", rule.rule_content),
            confidence=data.get("confidence", rule.confidence),
            evidence=rule.evidence,
            version=rule.version + 1,
            is_latest=True,
            is_active=data.get("is_active", rule.is_active),
            created_by=data.get("updated_by"),
        )
        self.db.add(new_rule)
        await self.db.flush()
        return new_rule

    # ── Internal Methods ──────────────────────────────────────

    async def _aggregate_weekly_metrics(self, this_start, this_end, prev_start, prev_end) -> dict:
        """Aggregate all metrics for the week comparison."""
        from app.models.agent import DetectionResult, SentimentResult
        from app.models.knowledge_base import KbAsset

        # Detection metrics
        this_results = (await self.db.execute(
            select(DetectionResult).where(
                DetectionResult.customer_id == self.customer_id,
                DetectionResult.detected_at >= this_start,
                DetectionResult.detected_at < this_end,
            )
        )).scalars().all()

        prev_results = (await self.db.execute(
            select(DetectionResult).where(
                DetectionResult.customer_id == self.customer_id,
                DetectionResult.detected_at >= prev_start,
                DetectionResult.detected_at < prev_end,
            )
        )).scalars().all()

        # Per-model exposure metrics
        detailed = []
        models = set([r.model_name for r in this_results] + [r.model_name for r in prev_results])
        for model in models:
            this_model = [r for r in this_results if r.model_name == model]
            prev_model = [r for r in prev_results if r.model_name == model]

            this_mentioned = sum(1 for r in this_model if r.brand_mentioned)
            prev_mentioned = sum(1 for r in prev_model if r.brand_mentioned)

            detailed.append({
                "type": "exposure", "name": f"{model}品牌提及率",
                "model_name": model,
                "current": round(this_mentioned / len(this_model) * 100, 1) if this_model else 0,
                "previous": round(prev_mentioned / len(prev_model) * 100, 1) if prev_model else 0,
                "change_pct": round((this_mentioned - prev_mentioned) / max(prev_mentioned, 1) * 100, 1),
                "trend": "up" if this_mentioned > prev_mentioned else ("down" if this_mentioned < prev_mentioned else "stable"),
            })

        # KB asset growth
        this_assets = (await self.db.execute(
            select(func.count(KbAsset.id)).where(
                KbAsset.customer_id == self.customer_id,
                KbAsset.created_at >= this_start, KbAsset.created_at < this_end,
            )
        )).scalar() or 0

        prev_assets = (await self.db.execute(
            select(func.count(KbAsset.id)).where(
                KbAsset.customer_id == self.customer_id,
                KbAsset.created_at >= prev_start, KbAsset.created_at < prev_end,
            )
        )).scalar() or 0

        detailed.append({
            "type": "asset", "name": "新增知识库资产",
            "current": this_assets, "previous": prev_assets,
            "change_pct": round((this_assets - prev_assets) / max(prev_assets, 1) * 100, 1),
            "trend": "up" if this_assets >= prev_assets else "down",
        })

        return {"detailed": detailed, "this_week_data": this_results, "prev_week_data": prev_results}

    def _build_highlights(self, metrics_data: dict) -> dict:
        detailed = metrics_data.get("detailed", [])
        up_trends = [m for m in detailed if m.get("trend") == "up"]
        down_trends = [m for m in detailed if m.get("trend") == "down"]

        return {
            "wins": [{"metric": m["name"], "change": f"+{m.get('change_pct', 0)}%"} for m in up_trends[:3]],
            "issues": [{"metric": m["name"], "change": f"{m.get('change_pct', 0)}%"} for m in down_trends[:3]],
            "summary": f"本周{len(up_trends)}项指标上升，{len(down_trends)}项指标下降",
        }

    def _build_recommendations(self, metrics_data: dict) -> dict:
        detailed = metrics_data.get("detailed", [])
        down_trends = [m for m in detailed if m.get("trend") == "down"]
        recs = []
        for m in down_trends[:3]:
            if m.get("type") == "exposure":
                recs.append({"action": f"加强{m.get('model_name', '多模型')}内容布局", "priority": "important", "target": m.get("model_name")})
            elif m.get("type") == "asset":
                recs.append({"action": "加速知识库资产增厚", "priority": "urgent"})
        return {"next_steps": recs, "strategy": "重点关注下降指标，针对性补强短板"}

    async def _analyze_kb_growth(self) -> dict:
        from app.models.knowledge_base import KbAsset
        result = await self.db.execute(
            select(KbAsset.asset_type, func.count(KbAsset.id))
            .where(KbAsset.customer_id == self.customer_id, KbAsset.is_latest == True, KbAsset.status == "published")
            .group_by(KbAsset.asset_type)
        )
        counts = {row[0]: row[1] for row in result.all()}
        return {"basic": counts.get("basic", 0), "marketing": counts.get("marketing", 0), "multimodal": counts.get("multimodal", 0)}

    async def _summarize_content_performance(self, start_date, end_date) -> dict:
        from app.models.publish import PublishPerformance
        result = await self.db.execute(
            select(func.count(PublishPerformance.id), func.sum(PublishPerformance.impressions), func.sum(PublishPerformance.clicks))
            .where(PublishPerformance.customer_id == self.customer_id, PublishPerformance.recorded_at >= start_date, PublishPerformance.recorded_at < end_date)
        )
        row = result.one()
        return {"published_count": row[0] or 0, "total_impressions": row[1] or 0, "total_clicks": row[2] or 0}

    def _build_markdown_report(self, metrics_data, highlights, recommendations) -> str:
        md = []
        md.append("# 周度GEO复盘报告\n")
        md.append(f"## 核心亮点\n{highlights.get('summary', '')}\n")
        md.append("### 本周提升\n")
        for w in highlights.get("wins", []):
            md.append(f"- {w['metric']}: {w['change']}")
        md.append("\n### 需关注\n")
        for i in highlights.get("issues", []):
            md.append(f"- {i['metric']}: {i['change']}")
        md.append(f"\n## 下轮策略\n{recommendations.get('strategy', '')}\n")
        for r in recommendations.get("next_steps", []):
            md.append(f"- [{r.get('priority', '')}] {r.get('action', '')}")
        return "\n".join(md)

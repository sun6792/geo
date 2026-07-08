"""P5 Sub-account management + customer portal data service."""

import uuid
from datetime import datetime, timezone, date
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.core.pagination import PaginationParams
from app.core.security import hash_password
from app.models.subscription import SubAccount, PaymentRecord
from app.models.customer import Customer
from app.models.agent import SourceVerification


class SubscriptionService:
    """Sub-account lifecycle management + payment tracking."""

    def __init__(self, db: AsyncSession, customer_id: uuid.UUID | None = None):
        self.db = db
        self.customer_id = customer_id

    # ── Sub-Accounts ─────────────────────────────────────────

    async def list_sub_accounts(self, pagination: PaginationParams) -> tuple[list[SubAccount], int]:
        query = select(SubAccount)
        count_q = select(func.count(SubAccount.id))
        if self.customer_id:
            query = query.where(SubAccount.customer_id == self.customer_id)
            count_q = count_q.where(SubAccount.customer_id == self.customer_id)
        total = (await self.db.execute(count_q)).scalar() or 0
        items = (await self.db.execute(
            query.order_by(SubAccount.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
        )).scalars().all()
        return list(items), total

    async def create_sub_account(self, data: dict) -> SubAccount:
        """Create a customer sub-account with auto-generated password if not provided."""
        if data.get("email"):
            existing = (await self.db.execute(
                select(SubAccount).where(SubAccount.email == data["email"])
            )).scalar_one_or_none()
            if existing:
                raise ValidationException(f"Sub-account with email '{data['email']}' already exists")

        password = data.pop("password", None) or "geo" + uuid.uuid4().hex[:8]
        sub = SubAccount(
            password_hash=hash_password(password),
            service_start=data.get("service_start", date.today()),
            **{k: v for k, v in data.items() if hasattr(SubAccount, k)}
        )
        self.db.add(sub)
        await self.db.flush()
        return sub, password  # Return plain password for initial delivery

    async def reset_password(self, sub_id: uuid.UUID) -> str:
        result = await self.db.execute(select(SubAccount).where(SubAccount.id == sub_id))
        sub = result.scalar_one_or_none()
        if not sub:
            raise NotFoundException("SubAccount", str(sub_id))
        new_pw = "geo" + uuid.uuid4().hex[:8]
        sub.password_hash = hash_password(new_pw)
        await self.db.flush()
        return new_pw

    async def toggle_sub_account(self, sub_id: uuid.UUID, is_active: bool) -> SubAccount:
        result = await self.db.execute(select(SubAccount).where(SubAccount.id == sub_id))
        sub = result.scalar_one_or_none()
        if not sub:
            raise NotFoundException("SubAccount", str(sub_id))
        sub.is_active = is_active
        await self.db.flush()
        return sub

    # ── Payment Records ──────────────────────────────────────

    async def list_payments(self, pagination: PaginationParams) -> tuple[list[PaymentRecord], int]:
        query = select(PaymentRecord)
        count_q = select(func.count(PaymentRecord.id))
        if self.customer_id:
            query = query.where(PaymentRecord.customer_id == self.customer_id)
            count_q = count_q.where(PaymentRecord.customer_id == self.customer_id)
        total = (await self.db.execute(count_q)).scalar() or 0
        items = (await self.db.execute(
            query.order_by(PaymentRecord.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
        )).scalars().all()
        return list(items), total

    async def create_payment(self, data: dict) -> PaymentRecord:
        rec = PaymentRecord(**{k: v for k, v in data.items() if hasattr(PaymentRecord, k)})
        self.db.add(rec)
        await self.db.flush()
        return rec

    async def create_sub_from_payment(self, payment_id: uuid.UUID, email: str, created_by: uuid.UUID) -> dict:
        """One-click: create sub-account from a payment record."""
        result = await self.db.execute(select(PaymentRecord).where(PaymentRecord.id == payment_id))
        payment = result.scalar_one_or_none()
        if not payment:
            raise NotFoundException("PaymentRecord", str(payment_id))

        password = "geo" + uuid.uuid4().hex[:8]
        sub = SubAccount(
            customer_id=payment.customer_id,
            email=email,
            password_hash=hash_password(password),
            display_name=payment.company_name,
            company_name=payment.company_name,
            service_start=payment.service_start,
            service_end=payment.service_end,
            created_by=created_by,
        )
        self.db.add(sub)
        await self.db.flush()

        payment.sub_account_id = sub.id
        await self.db.flush()
        return {"sub_account_id": str(sub.id), "email": email, "password": password}


class CustomerPortalService:
    """Read-only data queries for customer sub-account portal."""

    def __init__(self, db: AsyncSession, customer_id: uuid.UUID):
        self.db = db
        self.customer_id = customer_id

    async def get_daily_progress(self) -> dict:
        """Today's publishing and ranking progress."""
        today = date.today()
        from app.models.publish import PublishRecord, PublishPerformance
        from app.models.agent import DetectionResult

        # Today's published count
        pub_count = (await self.db.execute(
            select(func.count(PublishRecord.id)).where(
                PublishRecord.customer_id == self.customer_id,
                PublishRecord.publish_status == "success",
                func.date(PublishRecord.published_at) == today,
            )
        )).scalar() or 0

        # Today's detection results
        det_results = (await self.db.execute(
            select(DetectionResult).where(
                DetectionResult.customer_id == self.customer_id,
                func.date(DetectionResult.detected_at) == today,
            )
        )).scalars().all()

        models_data = {}
        for r in det_results:
            if r.model_name not in models_data:
                models_data[r.model_name] = {"count": 0, "rank_sum": 0, "rank_count": 0}
            models_data[r.model_name]["count"] += 1
            if r.rank_position:
                models_data[r.model_name]["rank_sum"] += r.rank_position
                models_data[r.model_name]["rank_count"] += 1

        ranking = []
        for model, data in models_data.items():
            avg_rank = round(data["rank_sum"] / data["rank_count"], 1) if data["rank_count"] else None
            ranking.append({"model": model, "mentions": data["count"], "avg_rank": avg_rank})

        return {
            "date": today.isoformat(),
            "published_today": pub_count,
            "model_rankings": ranking,
            "new_sources": (await self.db.execute(
                select(func.count(SourceVerification.id)).where(
                    SourceVerification.customer_id == self.customer_id,
                    func.date(SourceVerification.verified_at) == today,
                )
            )).scalar() or 0,
        }

    async def get_weekly_summary(self) -> dict:
        """Weekly performance summary."""
        from datetime import timedelta
        today = date.today()
        week_start = today - timedelta(days=today.weekday())

        from app.models.publish import PublishRecord
        from app.models.knowledge_base import KbAsset

        weekly_pubs = (await self.db.execute(
            select(func.count(PublishRecord.id)).where(
                PublishRecord.customer_id == self.customer_id,
                PublishRecord.publish_status == "success",
                func.date(PublishRecord.published_at) >= week_start,
            )
        )).scalar() or 0

        weekly_assets = (await self.db.execute(
            select(func.count(KbAsset.id)).where(
                KbAsset.customer_id == self.customer_id,
                KbAsset.is_latest == True,
                func.date(KbAsset.created_at) >= week_start,
            )
        )).scalar() or 0

        # ── Calculate real growth metrics ────────────────────────
        prev_week_start = week_start - timedelta(days=7)

        # Exposure growth: compare this week vs last week detection mentions
        from app.models.agent import DetectionResult, FiveDimScore
        this_week_mentions = (await self.db.execute(
            select(func.count(DetectionResult.id)).where(
                DetectionResult.customer_id == self.customer_id,
                DetectionResult.brand_mentioned == True,
                func.date(DetectionResult.detected_at) >= week_start,
            )
        )).scalar() or 1

        prev_week_mentions = (await self.db.execute(
            select(func.count(DetectionResult.id)).where(
                DetectionResult.customer_id == self.customer_id,
                DetectionResult.brand_mentioned == True,
                func.date(DetectionResult.detected_at) >= prev_week_start,
                func.date(DetectionResult.detected_at) < week_start,
            )
        )).scalar() or 1

        exposure_growth_pct = round((this_week_mentions - prev_week_mentions) / max(prev_week_mentions, 1) * 100, 1)
        exposure_growth = f"{'+' if exposure_growth_pct >= 0 else ''}{exposure_growth_pct}%"

        # Rank improvement: compare average rank
        this_week_ranks = (await self.db.execute(
            select(func.avg(DetectionResult.rank_position)).where(
                DetectionResult.customer_id == self.customer_id,
                DetectionResult.rank_position.isnot(None),
                func.date(DetectionResult.detected_at) >= week_start,
            )
        )).scalar()

        prev_week_ranks = (await self.db.execute(
            select(func.avg(DetectionResult.rank_position)).where(
                DetectionResult.customer_id == self.customer_id,
                DetectionResult.rank_position.isnot(None),
                func.date(DetectionResult.detected_at) >= prev_week_start,
                func.date(DetectionResult.detected_at) < week_start,
            )
        )).scalar()

        if this_week_ranks and prev_week_ranks:
            rank_improvement = round(prev_week_ranks - this_week_ranks, 1)
            rank_text = f"{'+' if rank_improvement > 0 else ''}{rank_improvement}位" if rank_improvement != 0 else "持平"
        else:
            rank_text = "暂无数据"

        # Weight score change: from FiveDimScore
        this_week_scores = (await self.db.execute(
            select(func.avg(FiveDimScore.total_score)).where(
                FiveDimScore.customer_id == self.customer_id,
                FiveDimScore.model_name.is_(None),  # overall score
                func.date(FiveDimScore.scored_at) >= week_start,
            )
        )).scalar()

        prev_week_scores = (await self.db.execute(
            select(func.avg(FiveDimScore.total_score)).where(
                FiveDimScore.customer_id == self.customer_id,
                FiveDimScore.model_name.is_(None),
                func.date(FiveDimScore.scored_at) >= prev_week_start,
                func.date(FiveDimScore.scored_at) < week_start,
            )
        )).scalar()

        if this_week_scores and prev_week_scores:
            score_change = round(this_week_scores - prev_week_scores, 1)
            score_text = f"{'+' if score_change > 0 else ''}{score_change}分" if score_change != 0 else "持平"
        else:
            score_text = "暂无数据"

        return {
            "week_start": week_start.isoformat(),
            "week_end": today.isoformat(),
            "total_published": weekly_pubs,
            "new_assets": weekly_assets,
            "exposure_growth": exposure_growth,
            "avg_rank_improvement": rank_text,
            "weight_score_change": score_text,
        }

    async def get_weekly_reviews(self) -> list:
        from app.models.publish import WeeklyReview
        result = await self.db.execute(
            select(WeeklyReview).where(WeeklyReview.customer_id == self.customer_id)
            .order_by(WeeklyReview.week_start.desc()).limit(12)
        )
        reviews = result.scalars().all()
        return [{"id": str(r.id), "week_start": r.week_start.isoformat(), "week_end": r.week_end.isoformat(),
                 "highlights": r.highlights, "recommendations": r.recommendations} for r in reviews]

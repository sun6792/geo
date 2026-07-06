"""Agent 1: Detection & Collection Service — multi-model probing, source verification, sentiment monitoring."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.core.pagination import PaginationParams
from app.models.agent import (
    DetectionTask, DetectionResult, Competitor,
    SourceVerification, SentimentResult,
)


class DetectionService:
    """Agent 1: Global detection, source verification, competitor tracking, sentiment monitoring."""

    def __init__(self, db: AsyncSession, customer_id: uuid.UUID):
        self.db = db
        self.customer_id = customer_id

    # ── Detection Tasks ───────────────────────────────────────

    async def list_tasks(self, pagination: PaginationParams) -> tuple[list[DetectionTask], int]:
        query = select(DetectionTask).where(DetectionTask.customer_id == self.customer_id)
        count_q = select(func.count(DetectionTask.id)).where(DetectionTask.customer_id == self.customer_id)
        total = (await self.db.execute(count_q)).scalar() or 0
        tasks = (await self.db.execute(
            query.order_by(DetectionTask.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
        )).scalars().all()
        return list(tasks), total

    async def create_task(self, data: dict) -> DetectionTask:
        task = DetectionTask(customer_id=self.customer_id, **data)
        self.db.add(task)
        await self.db.flush()
        return task

    async def get_task(self, task_id: uuid.UUID) -> DetectionTask:
        result = await self.db.execute(
            select(DetectionTask).where(DetectionTask.id == task_id, DetectionTask.customer_id == self.customer_id)
        )
        t = result.scalar_one_or_none()
        if not t:
            raise NotFoundException("DetectionTask", str(task_id))
        return t

    async def update_task(self, task_id: uuid.UUID, data: dict) -> DetectionTask:
        task = await self.get_task(task_id)
        for k, v in data.items():
            if v is not None and hasattr(task, k):
                setattr(task, k, v)
        await self.db.flush()
        return task

    async def delete_task(self, task_id: uuid.UUID) -> None:
        task = await self.get_task(task_id)
        await self.db.delete(task)
        await self.db.flush()

    async def run_detection(self, task_id: uuid.UUID) -> list[DetectionResult]:
        """Execute a detection run — probe all configured models with keywords."""
        task = await self.get_task(task_id)

        results = []
        # Simulate detection across models × keywords
        for keyword_obj in task.keywords:
            keyword = keyword_obj.get("word", "")
            kw_type = keyword_obj.get("type", "broad")
            for model in task.target_models:
                # In production, this would call actual LLM APIs
                result = DetectionResult(
                    customer_id=self.customer_id,
                    task_id=task_id,
                    model_name=model,
                    keyword=keyword,
                    keyword_type=kw_type,
                    brand_mentioned=False,  # will be filled by actual API
                    rank_position=None,
                    recommendation_level=None,
                    cited_sources=[],
                    exposure_count=0,
                )
                self.db.add(result)
                results.append(result)

        task.last_run_at = datetime.now(timezone.utc)
        task.last_status = "completed"
        await self.db.flush()
        return results

    # ── Detection Results ─────────────────────────────────────

    async def list_results(self, task_id: Optional[uuid.UUID] = None,
                            model_name: Optional[str] = None,
                            pagination: Optional[PaginationParams] = None) -> tuple[list[DetectionResult], int]:
        query = select(DetectionResult).where(DetectionResult.customer_id == self.customer_id)
        count_q = select(func.count(DetectionResult.id)).where(DetectionResult.customer_id == self.customer_id)

        if task_id:
            query = query.where(DetectionResult.task_id == task_id)
            count_q = count_q.where(DetectionResult.task_id == task_id)
        if model_name:
            query = query.where(DetectionResult.model_name == model_name)
            count_q = count_q.where(DetectionResult.model_name == model_name)

        total = (await self.db.execute(count_q)).scalar() or 0
        items = (await self.db.execute(
            query.order_by(DetectionResult.detected_at.desc())
            .offset(pagination.offset if pagination else 0)
            .limit(pagination.limit if pagination else 100)
        )).scalars().all()
        return list(items), total

    async def update_result(self, result_id: uuid.UUID, data: dict) -> DetectionResult:
        result = await self.db.execute(
            select(DetectionResult).where(DetectionResult.id == result_id, DetectionResult.customer_id == self.customer_id)
        )
        r = result.scalar_one_or_none()
        if not r:
            raise NotFoundException("DetectionResult", str(result_id))
        for k, v in data.items():
            if v is not None and hasattr(r, k):
                setattr(r, k, v)
        await self.db.flush()
        return r

    async def get_result_summary(self) -> dict:
        """Get detection summary for dashboards — aggregated by model."""
        results = (await self.db.execute(
            select(DetectionResult).where(DetectionResult.customer_id == self.customer_id)
        )).scalars().all()

        summary = {}
        for r in results:
            if r.model_name not in summary:
                summary[r.model_name] = {"total": 0, "mentioned": 0, "avg_rank": 0, "count": 0, "total_exposure": 0}
            summary[r.model_name]["total"] += 1
            summary[r.model_name]["total_exposure"] += r.exposure_count
            if r.brand_mentioned:
                summary[r.model_name]["mentioned"] += 1
            if r.rank_position is not None:
                summary[r.model_name]["avg_rank"] += r.rank_position
                summary[r.model_name]["count"] += 1

        for model, data in summary.items():
            data["mention_rate"] = round(data["mentioned"] / data["total"] * 100, 1) if data["total"] > 0 else 0
            data["avg_rank"] = round(data["avg_rank"] / data["count"], 1) if data["count"] > 0 else None

        return summary

    # ── Competitors ───────────────────────────────────────────

    async def list_competitors(self) -> list[Competitor]:
        result = await self.db.execute(
            select(Competitor).where(Competitor.customer_id == self.customer_id, Competitor.is_active == True)
        )
        return list(result.scalars().all())

    async def create_competitor(self, data: dict) -> Competitor:
        comp = Competitor(customer_id=self.customer_id, **data)
        self.db.add(comp)
        await self.db.flush()
        return comp

    async def update_competitor(self, comp_id: uuid.UUID, data: dict) -> Competitor:
        result = await self.db.execute(
            select(Competitor).where(Competitor.id == comp_id, Competitor.customer_id == self.customer_id)
        )
        c = result.scalar_one_or_none()
        if not c:
            raise NotFoundException("Competitor", str(comp_id))
        for k, v in data.items():
            if v is not None and hasattr(c, k):
                setattr(c, k, v)
        await self.db.flush()
        return c

    # ── Source Verifications ──────────────────────────────────

    async def list_source_verifications(self, is_consistent: Optional[bool] = None) -> list[SourceVerification]:
        query = select(SourceVerification).where(SourceVerification.customer_id == self.customer_id)
        if is_consistent is not None:
            query = query.where(SourceVerification.is_consistent == is_consistent)
        result = await self.db.execute(query.order_by(SourceVerification.verified_at.desc()).limit(200))
        return list(result.scalars().all())

    async def create_source_verification(self, data: dict) -> SourceVerification:
        sv = SourceVerification(customer_id=self.customer_id, **data)
        self.db.add(sv)
        await self.db.flush()
        return sv

    # ── Sentiment ─────────────────────────────────────────────

    async def list_sentiment_results(self, sentiment: Optional[str] = None,
                                      is_alert: Optional[bool] = None) -> list[SentimentResult]:
        query = select(SentimentResult).where(SentimentResult.customer_id == self.customer_id)
        if sentiment:
            query = query.where(SentimentResult.sentiment == sentiment)
        if is_alert is not None:
            query = query.where(SentimentResult.is_alert == is_alert)
        result = await self.db.execute(query.order_by(SentimentResult.detected_at.desc()).limit(200))
        return list(result.scalars().all())

    async def create_sentiment_result(self, data: dict) -> SentimentResult:
        sr = SentimentResult(customer_id=self.customer_id, **data)
        self.db.add(sr)
        await self.db.flush()
        return sr

    async def get_sentiment_summary(self) -> dict:
        """Get sentiment distribution summary for dashboards."""
        results = (await self.db.execute(
            select(SentimentResult).where(SentimentResult.customer_id == self.customer_id)
        )).scalars().all()

        summary = {"positive": 0, "neutral": 0, "negative": 0, "alert_count": 0, "total": len(results)}
        for r in results:
            if r.sentiment in summary:
                summary[r.sentiment] += 1
            if r.is_alert:
                summary["alert_count"] += 1
        return summary

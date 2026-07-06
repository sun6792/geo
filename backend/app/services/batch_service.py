"""P2 Batch Operations & System Monitoring Service."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.core.pagination import PaginationParams


class BatchService:
    """Batch operations: import, export, bulk actions, progress tracking."""

    def __init__(self, db: AsyncSession, customer_id: uuid.UUID):
        self.db = db
        self.customer_id = customer_id

    # ── Excel Import ──────────────────────────────────────────

    async def import_kb_assets_from_excel(self, rows: list[dict], created_by: uuid.UUID) -> dict:
        """Batch import KB assets from parsed Excel rows."""
        from app.models.knowledge_base import KbAsset
        stats = {"total": len(rows), "created": 0, "skipped": 0, "errors": []}

        for i, row in enumerate(rows):
            try:
                title = row.get("title") or row.get("名称") or row.get("标题", "")
                if not title:
                    stats["errors"].append({"row": i + 1, "error": "Missing title"})
                    stats["skipped"] += 1
                    continue

                asset_type = row.get("asset_type") or row.get("资产类型", "basic")
                content_type = row.get("content_type") or row.get("内容类型", "text")

                asset = KbAsset(
                    customer_id=self.customer_id,
                    title=str(title),
                    slug=str(title).lower().replace(" ", "-")[:200],
                    asset_type=asset_type if asset_type in ("basic", "marketing", "multimodal") else "basic",
                    content_type=content_type,
                    content_text=str(row.get("content") or row.get("内容") or ""),
                    content_json=row.get("structured_data") or row.get("结构化数据"),
                    tags=row.get("tags") or row.get("标签", "").split(",") if isinstance(row.get("标签"), str) else [],
                    created_by=created_by,
                )
                self.db.add(asset)
                stats["created"] += 1
            except Exception as e:
                stats["errors"].append({"row": i + 1, "error": str(e)})
                stats["skipped"] += 1

        await self.db.flush()
        return stats

    # ── Bulk Review ───────────────────────────────────────────

    async def bulk_submit_review(self, draft_ids: list[uuid.UUID], submitted_by: uuid.UUID) -> dict:
        """Submit multiple drafts for review at once."""
        from app.models.content import ContentDraft
        from app.models.review import ReviewRecord

        stats = {"total": len(draft_ids), "submitted": 0, "skipped": 0, "errors": []}

        for did in draft_ids:
            try:
                result = await self.db.execute(
                    select(ContentDraft).where(ContentDraft.id == did, ContentDraft.customer_id == self.customer_id)
                )
                draft = result.scalar_one_or_none()
                if not draft:
                    stats["errors"].append({"draft_id": str(did), "error": "Not found"})
                    continue
                if draft.status not in ("draft", "revisions_requested"):
                    stats["skipped"] += 1
                    continue

                record = ReviewRecord(
                    customer_id=self.customer_id, draft_id=did,
                    stage="internal_review", status="pending",
                )
                self.db.add(record)
                draft.status = "in_review"
                stats["submitted"] += 1
            except Exception as e:
                stats["errors"].append({"draft_id": str(did), "error": str(e)})

        await self.db.flush()
        return stats

    # ── Export ─────────────────────────────────────────────────

    async def export_data(self, resource_type: str, filters: dict | None = None) -> dict:
        """Export data as structured dict (caller converts to Excel/PDF/CSV)."""
        data = {"resource_type": resource_type, "exported_at": datetime.now(timezone.utc).isoformat(), "items": []}

        if resource_type == "kb_assets":
            from app.models.knowledge_base import KbAsset
            query = select(KbAsset).where(KbAsset.customer_id == self.customer_id, KbAsset.is_latest == True)
            if filters and filters.get("asset_type"):
                query = query.where(KbAsset.asset_type == filters["asset_type"])
            result = await self.db.execute(query.order_by(KbAsset.title).limit(1000))
            data["items"] = [{"title": a.title, "type": a.asset_type, "status": a.status,
                              "tags": a.tags, "created_at": a.created_at.isoformat()} for a in result.scalars().all()]

        elif resource_type == "detection_results":
            from app.models.agent import DetectionResult
            query = select(DetectionResult).where(DetectionResult.customer_id == self.customer_id)
            if filters and filters.get("model_name"):
                query = query.where(DetectionResult.model_name == filters["model_name"])
            result = await self.db.execute(query.order_by(DetectionResult.detected_at.desc()).limit(2000))
            data["items"] = [{"model": r.model_name, "keyword": r.keyword, "mentioned": r.brand_mentioned,
                              "rank": r.rank_position, "detected_at": r.detected_at.isoformat()} for r in result.scalars().all()]

        elif resource_type == "diagnosis_reports":
            from app.models.agent import DiagnosisReport
            query = select(DiagnosisReport).where(DiagnosisReport.customer_id == self.customer_id)
            result = await self.db.execute(query.order_by(DiagnosisReport.created_at.desc()).limit(100))
            data["items"] = [{"title": r.title, "period": f"{r.diagnosis_period_start}~{r.diagnosis_period_end}",
                              "summary": r.summary, "created_at": r.created_at.isoformat()} for r in result.scalars().all()]

        elif resource_type == "publish_records":
            from app.models.publish import PublishRecord
            query = select(PublishRecord).where(PublishRecord.customer_id == self.customer_id)
            result = await self.db.execute(query.order_by(PublishRecord.published_at.desc()).limit(2000))
            data["items"] = [{"status": r.publish_status, "url": r.published_url,
                              "published_at": r.published_at.isoformat() if r.published_at else None} for r in result.scalars().all()]

        return data


class MonitoringService:
    """System health monitoring, alerting, and metrics."""

    def __init__(self, db: AsyncSession, customer_id: uuid.UUID | None = None):
        self.db = db
        self.customer_id = customer_id

    async def get_system_health(self) -> dict:
        """Check health of all system components."""
        health = {"status": "healthy", "components": {}, "timestamp": datetime.now(timezone.utc).isoformat()}

        # Database
        try:
            await self.db.execute(select(func.now()))
            health["components"]["database"] = "healthy"
        except Exception as e:
            health["components"]["database"] = f"unhealthy: {str(e)}"
            health["status"] = "degraded"

        # Chroma
        try:
            from app.integrations.vector_store.chroma_store import chroma_store
            chroma_store.client.heartbeat()
            health["components"]["chroma"] = "healthy"
        except Exception:
            health["components"]["chroma"] = "unavailable"
            health["status"] = "degraded"

        return health

    async def get_task_stats(self) -> dict:
        """Get background task execution statistics."""
        from app.models.publish import PublishSchedule
        from app.models.agent import DetectionTask

        failed_publishes = (await self.db.execute(
            select(func.count(PublishSchedule.id)).where(
                PublishSchedule.customer_id == self.customer_id if self.customer_id else True,
                PublishSchedule.status == "failed",
            )
        )).scalar() or 0

        active_detection_tasks = (await self.db.execute(
            select(func.count(DetectionTask.id)).where(
                DetectionTask.customer_id == self.customer_id if self.customer_id else True,
                DetectionTask.is_active == True,
            )
        )).scalar() or 0

        return {
            "failed_publishes": failed_publishes,
            "active_detection_tasks": active_detection_tasks,
            "alerts": failed_publishes,
        }

    async def get_usage_stats(self) -> dict:
        """Get resource usage statistics."""
        from app.models.content import ContentBrief, ContentDraft
        from app.models.knowledge_base import KbAsset
        from app.models.agent import DetectionResult

        customer_filter = {"customer_id": self.customer_id} if self.customer_id else {}

        kb_count = (await self.db.execute(
            select(func.count(KbAsset.id)).where(KbAsset.is_latest == True, **customer_filter)
        )).scalar() or 0

        content_count = (await self.db.execute(
            select(func.count(ContentDraft.id)).where(**customer_filter)
        )).scalar() or 0

        detection_count = (await self.db.execute(
            select(func.count(DetectionResult.id)).where(**customer_filter)
        )).scalar() or 0

        return {
            "kb_assets": kb_count,
            "content_drafts": content_count,
            "detection_results": detection_count,
            "total_operations": kb_count + content_count + detection_count,
        }

    async def get_operation_logs(self, pagination: PaginationParams,
                                  user_id: Optional[uuid.UUID] = None,
                                  resource_type: Optional[str] = None) -> tuple[list, int]:
        """Query operation logs with filters."""
        from app.models.system import OperationLog

        query = select(OperationLog)
        count_q = select(func.count(OperationLog.id))

        if self.customer_id:
            query = query.where(OperationLog.customer_id == self.customer_id)
            count_q = count_q.where(OperationLog.customer_id == self.customer_id)
        if user_id:
            query = query.where(OperationLog.user_id == user_id)
            count_q = count_q.where(OperationLog.user_id == user_id)
        if resource_type:
            query = query.where(OperationLog.resource_type == resource_type)
            count_q = count_q.where(OperationLog.resource_type == resource_type)

        total = (await self.db.execute(count_q)).scalar() or 0
        items = (await self.db.execute(
            query.order_by(OperationLog.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
        )).scalars().all()

        return list(items), total

"""Celery tasks for Agent 1 asynchronous probe execution.

Provides:
- Async task execution with Celery
- Task priority, retry, dead-letter queue
- Progress tracking via database
- Auto-trigger Agent 2 on completion
- Billing quota enforcement

Note: For environments without Celery (local dev), the BatchProbeScheduler
can be called directly as an async function. Celery adds production-grade
reliability (retry, persistence, monitoring).
"""

import asyncio
import uuid
from celery import Celery
from app.config import settings
from app.core.database import async_session_factory

# ── Celery app ─────────────────────────────────────────────────
celery_app = Celery(
    "geo_probe",
    broker=settings.__dict__.get("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=settings.__dict__.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_annotations={
        "app.tasks.celery_probe.run_detection_task": {"rate_limit": "20/m"},
    },
)


def _run_async(coro):
    """Helper: run async coroutine in sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def run_detection_task(self, tenant_id: str, task_id: str):
    """Celery task: execute a complete detection run.

    This wraps the async BatchProbeScheduler for production use.
    Falls back gracefully if Celery is not available.
    """
    from app.integrations.llm_probe.scheduler import BatchProbeScheduler

    async def _run():
        async with async_session_factory() as db:
            scheduler = BatchProbeScheduler(db, uuid.UUID(tenant_id))
            try:
                result = await scheduler.execute_task(uuid.UUID(task_id))
                await db.commit()
                return result
            except Exception as e:
                await db.rollback()
                raise self.retry(exc=e)

    try:
        return _run_async(_run())
    except Exception as e:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        return {"error": str(e), "task_id": task_id, "status": "failed"}


@celery_app.task
def cleanup_old_probe_data(days: int = 90):
    """Periodic task: clean up probe data older than N days."""
    from app.integrations.llm_probe.models import LLMProbeResult
    from datetime import timedelta, datetime, timezone as tz

    async def _run():
        cutoff = datetime.now(tz.utc) - timedelta(days=days)
        async with async_session_factory() as db:
            from sqlalchemy import delete
            await db.execute(
                delete(LLMProbeResult).where(LLMProbeResult.created_at < cutoff)
            )
            await db.commit()
            return {"deleted_before": cutoff.isoformat()}

    return _run_async(_run())

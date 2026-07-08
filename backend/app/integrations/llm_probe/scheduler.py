"""Batch Probe Scheduler — orchestrates full multi-model detection task.

Flow:
  1. Receive DetectionTask
  2. Generate questions via QueryGenerator
  3. Create ProbeTaskProgress
  4. Execute probes across all models IN PARALLEL
  5. For each answer: parse via DeepSeek Function Calling
  6. For brand-not-mentioned: auto follow-up round
  7. Persist all results to LLMProbeResult
  8. Update progress in real-time
  9. Callback: trigger Agent2 diagnosis
  10. Billing: deduct quota via billing_service
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.llm_probe.base import ProbeResult
from app.integrations.llm_probe.factory import LLMProbeFactory
from app.integrations.llm_probe.unbiased_query_generator import UnbiasedQueryGenerator
from app.integrations.llm_probe.authentic_parser import AuthenticParser
from app.integrations.llm_probe.models import LLMProbeResult, ProbeTaskProgress
from app.models.agent import DetectionTask, Competitor
from app.models.customer import Customer
from app.core.exceptions import ValidationException


class BatchProbeScheduler:
    """Orchestrates complete multi-model detection workflow."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.factory = LLMProbeFactory()
        self.query_gen = UnbiasedQueryGenerator()  # V2: 70/20/10 unbiased
        self.parser = AuthenticParser()           # V2: three-layer authentic parsing

    async def execute_task(self, task_id: uuid.UUID) -> dict:
        """Execute a complete detection task across all models.

        This is the main entry point. Can be called directly (async)
        or via Celery task wrapper.
        """
        # ── 1. Load task ───────────────────────────────────────
        task = await self._get_task(task_id)
        customer = await self._get_customer()
        company_name = customer.company_name or customer.name
        industry = customer.industry or ""
        main_business = ""
        if task.keywords:
            main_business = task.keywords[0].get("word", "")

        competitor_names = await self._get_competitor_names(task)

        # ── 2. Generate unbiased queries (70/20/10 ratio) ──────
        region = getattr(customer, 'region', '') or ''
        query_bundle = await self.query_gen.generate(
            company_name, industry, main_business, competitor_names, region, count=15,
        )
        # Natural ranking queries (70% pain + 20% comparison) — used for scoring
        natural_queries = query_bundle["natural_ranking_queries"]
        # Brand verification queries (10% brand) — identity check only, NOT scored
        brand_queries = query_bundle["brand_verification_queries"]

        target_models = task.target_models or LLMProbeFactory.get_available_models()

        # Build task queries: natural queries go to all models
        all_queries = []
        for q_text in natural_queries:
            for model_id in target_models:
                all_queries.append({"type": "natural_ranking", "question": q_text, "model_id": model_id, "scored": True})
        for q_text in brand_queries:
            for model_id in target_models:
                all_queries.append({"type": "brand_verification", "question": q_text, "model_id": model_id, "scored": False})

        # ── 2.5 Competitor parity: same questions, same models ──
        for comp_name in competitor_names[:3]:
            comp_queries = await self.query_gen.generate(
                comp_name, industry, main_business, competitor_names, region, count=6,
            )
            for q_text in comp_queries.get("natural_ranking_queries", [])[:4]:
                for model_id in target_models[:2]:  # Only first 2 models for competitor
                    all_queries.append({
                        "type": "competitor_parity", "question": q_text,
                        "model_id": model_id, "scored": False,
                        "competitor_name": comp_name,
                    })

        # ── 3. Create progress tracker ─────────────────────────
        progress = ProbeTaskProgress(
            tenant_id=self.tenant_id, task_id=task_id,
            total_queries=len(all_queries),
            model_progress={m: {"total": len(queries), "done": 0, "failed": 0}
                            for m in target_models},
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(progress)
        await self.db.flush()

        # Update task status
        task.last_status = "running"
        await self.db.flush()

        # ── 4. Execute all probes in parallel ──────────────────
        probes = LLMProbeFactory.create_all()
        sem = asyncio.Semaphore(10)  # max 10 concurrent API calls

        async def probe_one(q: dict) -> LLMProbeResult:
            model_id = q["model_id"]
            probe = probes.get(model_id)
            if not probe:
                return self._skipped_result(q, task_id, "Model not configured")

            async with sem:
                # First round
                result = await probe.query(q["question"])
                record = await self._save_result(result, q, task_id)

                # Auto follow-up if brand not found
                if result.status == "success" and not self._brand_in_answer(
                        result.raw_answer, company_name):
                    follow_up = await probe.query_follow_up(
                        q["question"], result.raw_answer, company_name
                    )
                    await self._save_result(follow_up, q, task_id, is_follow_up=True)

                # Update progress
                mp = progress.model_progress.get(model_id, {})
                mp["done"] = mp.get("done", 0) + 1
                if result.status != "success":
                    mp["failed"] = mp.get("failed", 0) + 1
                progress.model_progress[model_id] = mp
                progress.completed_queries += 1
                if result.status != "success":
                    progress.failed_queries += 1
                await self.db.flush()

                return record

        t0 = time.time()
        results = await asyncio.gather(*[probe_one(q) for q in all_queries])

        # ── 5. Finalize ────────────────────────────────────────
        progress.completed_at = datetime.now(timezone.utc)
        task.last_run_at = datetime.now(timezone.utc)
        task.last_status = "completed"
        await self.db.flush()

        # ── 6. Billing: deduct quota ───────────────────────────
        total_tokens = sum((r.input_tokens + r.output_tokens) for r in results if r)
        await self._deduct_quota(total_tokens)

        # ── 7. Callback: trigger Agent2 diagnosis ──────────────
        try:
            from app.services.layered_diagnosis.enhanced_service import EnhancedDiagnosisService
            diag_svc = EnhancedDiagnosisService(self.db, self.tenant_id)
            await diag_svc.run_full_diagnosis(
                generated_by=uuid.UUID(int=0),
                detection_task_id=task_id,
            )
        except Exception as e:
            print(f"[Scheduler] Auto-diagnosis trigger failed: {e}")

        return {
            "task_id": str(task_id),
            "total_queries": len(all_queries),
            "total_models": len(target_models),
            "success_count": sum(1 for r in results if r and r.status == "success"),
            "failed_count": sum(1 for r in results if r and r.status != "success"),
            "total_tokens": total_tokens,
            "duration_sec": round(time.time() - t0, 1),
        }

    async def _save_result(self, result: ProbeResult, query: dict,
                            task_id: uuid.UUID, is_follow_up: bool = False) -> LLMProbeResult:
        """Persist a probe result with authentic parsing + full raw data."""
        # ── Parse via AuthenticParser (three-layer) ────────────
        identity = self._build_identity_baseline()
        competitor_names = [c for c in query.get("competitor_names", []) if c]

        if result.status == "success" and result.raw_answer:
            parsed = await self.parser.parse(
                result.raw_answer, identity, competitor_names,
            )
        else:
            parsed = {
                "is_valid_mention": False, "mention_type": "irrelevant",
                "rank_position": 0, "info_accuracy_score": 0,
                "error_details": [], "negative_details": [],
                "recommended_competitors": [],
                "judge_basis": "API failure", "confidence": 0.0,
                "parser_layer": "skipped", "suggested_review": False,
            }

        cost = (result.input_tokens / 1000 * 0.001 +
                result.output_tokens / 1000 * 0.002)

        record = LLMProbeResult(
            tenant_id=self.tenant_id, task_id=task_id,
            model_id=result.model_id, model_name=result.model_name,
            query_text=result.query_text,
            query_type="follow_up" if is_follow_up else query.get("type", "first_round"),
            raw_answer=result.raw_answer,
            brand_mentioned=parsed.get("is_valid_mention", False),
            brand_rank=parsed.get("rank_position", 0),
            mentioned_competitors=parsed.get("recommended_competitors", []),
            has_error_info=parsed.get("error_details", []) != [],
            error_details=parsed.get("error_details", []),
            has_negative=parsed.get("mention_type") == "negative_comment",
            negative_details=parsed.get("negative_details", []),
            info_consistency_score=parsed.get("info_accuracy_score", 0),
            input_tokens=result.input_tokens, output_tokens=result.output_tokens,
            estimated_cost=cost,
            probe_duration_ms=result.probe_duration_ms,
            status=result.status,
            error_message=result.error_message[:500] if result.error_message else None,
            # ── Authenticity fields ───────────────────────────
            probe_mode=result.probe_mode,
            confidence=parsed.get("confidence", 1.0),
            has_search_source=result.has_search_source,
            raw_request=result.raw_request,
            raw_response=result.raw_response,
            api_request_id=result.api_request_id,
            model_version=result.model_version,
            search_engine_name="native" if result.has_search_source else None,
            query_variant_group=query.get("variant_group"),
        )
        self.db.add(record)
        await self.db.flush()
        return record

    def _build_identity_baseline(self) -> dict:
        """Build identity baseline from customer data (simplified)."""
        return {
            "full_name": "",
            "short_name": "",
            "aliases": [],
            "brand_names": [],
            "product_names": [],
            "key_people": [],
        }

    @staticmethod
    def _skipped_result(query: dict, task_id: uuid.UUID, reason: str) -> LLMProbeResult:
        return LLMProbeResult(
            tenant_id=uuid.UUID(int=0), task_id=task_id,
            model_id=query.get("model_id", "unknown"),
            model_name=query.get("model_id", "unknown"),
            query_text=query.get("question", ""),
            raw_answer="", status="skipped", error_message=reason,
        )

    @staticmethod
    def _brand_in_answer(answer: str, company: str) -> bool:
        return company[:4].lower() in answer.lower() if len(company) >= 4 else False

    async def _deduct_quota(self, tokens: int):
        """Deduct tenant quota via billing service."""
        try:
            from app.services.billing_service import BillingService
            svc = BillingService(self.db, self.tenant_id)
            await svc.record_usage("llm_tokens", tokens)
        except Exception:
            pass  # Non-critical, don't block the task

    async def _get_task(self, task_id: uuid.UUID) -> DetectionTask:
        r = await self.db.execute(
            select(DetectionTask).where(
                DetectionTask.id == task_id,
                DetectionTask.customer_id == self.tenant_id,
            )
        )
        task = r.scalar_one_or_none()
        if not task:
            raise ValidationException("DetectionTask not found")
        return task

    async def _get_customer(self) -> Customer:
        r = await self.db.execute(select(Customer).where(Customer.id == self.tenant_id))
        return r.scalar_one_or_none()

    async def _get_competitor_names(self, task: DetectionTask) -> list[str]:
        if not task.competitor_ids:
            return []
        r = await self.db.execute(
            select(Competitor.name).where(
                Competitor.id.in_(task.competitor_ids),
                Competitor.customer_id == self.tenant_id,
            )
        )
        return [row[0] for row in r.all()]

    async def close(self):
        await self.query_gen.close()
        await self.parser.close()

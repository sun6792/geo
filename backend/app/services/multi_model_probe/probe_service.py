"""P6: Multi-Model Probe Orchestration Service.

The main service that coordinates the entire probe workflow:
1. Auto-generate question sets from enterprise identity profile
2. Execute parallel multi-model probing with rate limiting
3. Parse responses via DeepSeek structured extraction
4. Persist raw responses + structured results + statistics
5. Feed data to downstream Agent2/Agent3/Agent5
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.agent import DetectionTask, DetectionResult, Competitor
from app.models.identity import EnterpriseIdentityProfile
from app.core.exceptions import NotFoundException, ValidationException

from app.services.multi_model_probe.models import (
    ModelProbeResponse, ProbeExtraction, ProbeExecutionLog, ProbeStatistics,
)
from app.services.multi_model_probe.probe_base import (
    ProbeRequest, ProbeResponse, ProbeStatus, RateLimiter,
)
from app.services.multi_model_probe.probe_adapters import (
    create_all_probes, PROBE_REGISTRY,
)
from app.services.multi_model_probe.result_parser import ProbeResultParser


# ════════════════════════════════════════════════════════════════
# Question generation from identity baseline
# ════════════════════════════════════════════════════════════════

PROBE_QUESTION_TEMPLATES = {
    "broad": [
        "国内做{industry}的厂家有哪些？请列举你知道的。",
        "{industry}行业有哪些知名的生产企业？",
        "我想了解一下{industry}行业的优质供应商。",
    ],
    "product": [
        "能做{main_business}的工厂有哪几家？给出企业名称和核心优势。",
        "{main_business}方面，国内哪些厂家做得比较好？",
        "想找做{main_business}的源头工厂，有什么推荐？",
    ],
    "comparison": [
        "{company_name}和{rival_name}在{industry}领域哪家更值得推荐？从实力、口碑、线上影响力综合对比。",
        "如果要在{company_name}和{rival_name}中选一家{main_business}供应商，你推荐哪家？为什么？",
    ],
    "scenario": [
        "我需要采购{main_business}，预算中等，对品质有要求，推荐几家靠谱的厂家？",
        "想找一家做{main_business}的工厂，要求有实力、资质齐全，有什么推荐？",
        "准备采购一批{main_business}，有没有性价比高的厂家推荐？",
    ],
    "pain_point": [
        "{industry}行业采购中常见的问题有哪些？哪家能比较好地解决这些痛点？",
        "做{main_business}的厂家一般容易出什么问题？有谁做得特别好的？",
    ],
}


# ════════════════════════════════════════════════════════════════
# Main orchestration service
# ════════════════════════════════════════════════════════════════

class MultiModelProbeService:
    """Orchestrates the complete multi-model probe workflow.

    Usage:
        service = MultiModelProbeService(db, customer_id)
        execution = await service.start_probe(task_id)
        # Monitor: execution.status
        # Results: await service.get_results(task_id)
    """

    def __init__(self, db: AsyncSession, customer_id: uuid.UUID):
        self.db = db
        self.customer_id = customer_id
        self.api_key = settings.OPENAI_API_KEY or ""
        self.parser = ProbeResultParser(self.api_key)
        self.rate_limiter = RateLimiter(
            max_requests_per_second=2.0,
            max_concurrent=3,
            burst_size=5,
        )

    # ════════════════════════════════════════════════════════════
    # Main workflow
    # ════════════════════════════════════════════════════════════

    async def start_probe(self, task_id: uuid.UUID) -> ProbeExecutionLog:
        """Start a full multi-model probe execution for a detection task.

        This is the main entry point. It:
        1. Loads the detection task and enterprise identity
        2. Generates the question set
        3. Creates execution log
        4. Launches async probing across all target models
        5. Automatically parses and persists results
        """
        # 1. Load task
        task = await self._get_task(task_id)

        # 2. Load enterprise identity baseline
        identity = await self._get_identity()

        # 3. Load competitors
        competitor_names = await self._get_competitor_names(task)

        # 4. Generate question set
        questions = self._generate_question_set(task, identity, competitor_names)

        # 5. Create execution log
        execution = ProbeExecutionLog(
            customer_id=self.customer_id,
            task_id=task_id,
            status="running",
            total_questions=len(questions),
            started_at=datetime.now(timezone.utc),
            model_progress={
                m: {"status": "pending", "questions": 0, "success": 0, "failed": 0}
                for m in task.target_models
            },
        )
        self.db.add(execution)
        await self.db.flush()

        # 6. Update task status
        task.last_status = "running"
        await self.db.flush()

        # 7. Launch async probing (fire-and-forget for API, but we await here)
        try:
            await self._execute_probes(execution, task, questions,
                                        identity, competitor_names)

            # 8. Compute statistics
            await self._compute_statistics(execution, task)

            # 9. Mark complete
            execution.status = "completed"
            execution.completed_at = datetime.now(timezone.utc)
            task.last_run_at = datetime.now(timezone.utc)
            task.last_status = "completed"

        except Exception as e:
            execution.status = "failed"
            execution.errors.append({
                "phase": "execution",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            task.last_status = "failed"

        await self.db.flush()
        return execution

    # ════════════════════════════════════════════════════════════
    # Core execution
    # ════════════════════════════════════════════════════════════

    async def _execute_probes(self, execution: ProbeExecutionLog,
                               task: DetectionTask,
                               questions: list[dict],
                               identity: EnterpriseIdentityProfile | None,
                               competitor_names: list[str]):
        """Execute all probes across models with rate limiting."""

        company_name = identity.company_name if identity else "未命名企业"
        known_facts = self._build_known_facts(identity) if identity else ""

        # Create probes for target models
        target_models = task.target_models or list(PROBE_REGISTRY.keys())
        probes = create_all_probes(self.api_key, target_models, self.rate_limiter)

        all_probe_requests: list[ProbeRequest] = []
        for q in questions:
            if q["model"] not in probes:
                continue
            req = ProbeRequest(
                question=q["question"],
                system_prompt=probes[q["model"]].default_persona,
                model_key=q["model"],
                model_cn=PROBE_REGISTRY[q["model"]]["model_cn"],
                keyword=q["keyword"],
                keyword_type=q["keyword_type"],
                question_round=q.get("round", 1),
            )
            all_probe_requests.append(req)

        # Execute in batches of max_concurrent
        sem = asyncio.Semaphore(self.rate_limiter.max_concurrent)
        total = len(all_probe_requests)
        completed = 0

        async def probe_one(req: ProbeRequest):
            nonlocal completed
            async with sem:
                probe = probes[req.model_key]
                response = await probe.probe(req)

                # Persist raw response
                raw = await self._save_raw_response(req, response, execution)

                # Parse and persist structured extraction
                if response.status == ProbeStatus.SUCCESS and response.response_text:
                    extraction_data = await self.parser.extract(
                        response.response_text, company_name,
                        competitor_names, known_facts,
                    )
                    await self._save_extraction(raw, extraction_data, execution)

                # Update execution progress
                completed += 1
                execution.completed_questions = completed
                if response.status == ProbeStatus.SUCCESS:
                    execution.successful_questions += 1
                else:
                    execution.failed_questions += 1
                    execution.errors.append({
                        "model": req.model_key,
                        "keyword": req.keyword,
                        "round": req.question_round,
                        "error": response.error_message,
                        "status": response.status.value,
                    })

                # Update per-model progress
                mp = execution.model_progress.get(req.model_key, {})
                mp["questions"] = mp.get("questions", 0) + 1
                if response.status == ProbeStatus.SUCCESS:
                    mp["success"] = mp.get("success", 0) + 1
                else:
                    mp["failed"] = mp.get("failed", 0) + 1
                execution.model_progress[req.model_key] = mp

                return response

        t0 = time.time()
        await asyncio.gather(*[probe_one(req) for req in all_probe_requests])

        execution.total_duration_ms = int((time.time() - t0) * 1000)

    # ════════════════════════════════════════════════════════════
    # Persistence helpers
    # ════════════════════════════════════════════════════════════

    async def _save_raw_response(self, request: ProbeRequest,
                                   response: ProbeResponse,
                                   execution: ProbeExecutionLog) -> ModelProbeResponse:
        """Persist a raw probe response."""
        raw = ModelProbeResponse(
            customer_id=self.customer_id,
            task_id=execution.task_id,
            model_name=request.model_key,
            model_cn=request.model_cn,
            question_round=request.question_round,
            keyword=request.keyword,
            keyword_type=request.keyword_type,
            question_text=request.question,
            system_prompt=request.system_prompt,
            request_params={
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
            },
            response_text=response.response_text,
            response_length=len(response.response_text),
            tokens_input=response.tokens_input,
            tokens_output=response.tokens_output,
            api_latency_ms=response.latency_ms,
            execution_status=response.status.value,
            error_message=response.error_message,
            retry_count=response.retry_count,
            is_fallback_response=response.is_fallback,
            api_provider=response.api_provider,
            api_model_id=response.api_model_id,
        )
        self.db.add(raw)
        await self.db.flush()
        return raw

    async def _save_extraction(self, raw: ModelProbeResponse,
                                 data: dict,
                                 execution: ProbeExecutionLog) -> ProbeExtraction:
        """Persist a parsed extraction result."""
        ext = ProbeExtraction(
            customer_id=self.customer_id,
            response_id=raw.id,
            task_id=execution.task_id,
            brand_mentioned=data.get("brand_mentioned", False),
            brand_name_found=data.get("brand_name_found"),
            mention_count=data.get("mention_count", 0),
            rank_position=data.get("rank_position"),
            rank_in_category=data.get("rank_in_category"),
            competitors_mentioned=data.get("competitors_mentioned", []),
            recommends_competitor=data.get("recommends_competitor", False),
            preferred_competitor=data.get("preferred_competitor"),
            competitor_advantage_summary=data.get("competitor_advantage_summary"),
            info_is_accurate=data.get("info_is_accurate", True),
            info_conflicts=data.get("info_conflicts", []),
            inconsistency_score=data.get("consistency_score", 1.0),
            negative_detected=data.get("negative_detected", False),
            negative_content=data.get("negative_content"),
            negative_category=data.get("negative_category"),
            risk_level=data.get("risk_level"),
            cited_sources=data.get("cited_sources", []),
            source_count=data.get("source_count", 0),
            authoritative_source_count=data.get("authoritative_source_count", 0),
            response_sentiment=data.get("response_sentiment"),
            parsing_confidence=data.get("parsing_confidence", 0.0),
            parser_model=data.get("parser_model"),
            parser_version=data.get("parser_version"),
            parsing_raw_output=data.get("parsing_raw_output"),
        )
        self.db.add(ext)
        await self.db.flush()

        # Also create/update DetectionResult for backward compatibility
        existing = (await self.db.execute(
            select(DetectionResult).where(
                DetectionResult.task_id == execution.task_id,
                DetectionResult.model_name == raw.model_name,
                DetectionResult.keyword == raw.keyword,
            )
        )).scalars().all()

        if not existing:
            result = DetectionResult(
                customer_id=self.customer_id,
                task_id=execution.task_id,
                model_name=raw.model_name,
                keyword=raw.keyword,
                keyword_type=raw.keyword_type,
                brand_mentioned=data.get("brand_mentioned", False),
                rank_position=data.get("rank_position"),
                recommendation_level="high" if data.get("rank_position") and data["rank_position"] <= 3 else (
                    "medium" if data.get("rank_position") and data["rank_position"] <= 5 else (
                        "low" if data.get("brand_mentioned") else "none"
                    )
                ),
                cited_sources=data.get("cited_sources", []),
                exposure_count=data.get("mention_count", 0),
                raw_response=raw.response_text[:2000],
                result_metadata={
                    "extraction_id": str(ext.id),
                    "response_id": str(raw.id),
                    "sentiment": data.get("response_sentiment"),
                    "negative_detected": data.get("negative_detected"),
                },
            )
            self.db.add(result)
            raw.result_id = result.id

        return ext

    # ════════════════════════════════════════════════════════════
    # Statistics computation
    # ════════════════════════════════════════════════════════════

    async def _compute_statistics(self, execution: ProbeExecutionLog,
                                    task: DetectionTask):
        """Compute aggregate statistics after all probes complete."""
        extractions = (await self.db.execute(
            select(ProbeExtraction).where(
                ProbeExtraction.customer_id == self.customer_id,
                ProbeExtraction.task_id == execution.task_id,
            )
        )).scalars().all()

        # Overall stats
        overall = ProbeResultParser.aggregate_statistics(
            [self._extraction_to_dict(e) for e in extractions]
        )
        self.db.add(ProbeStatistics(
            customer_id=self.customer_id,
            task_id=execution.task_id,
            model_name=None,
            keyword_type=None,
            **overall,
        ))

        # Per-model stats
        for model in task.target_models:
            model_extractions = [self._extraction_to_dict(e) for e in extractions
                                  if e.response and e.response.model_name == model]
            if model_extractions:
                stats = ProbeResultParser.aggregate_statistics(model_extractions, model)
                self.db.add(ProbeStatistics(
                    customer_id=self.customer_id,
                    task_id=execution.task_id,
                    model_name=model,
                    keyword_type=None,
                    **stats,
                ))

    @staticmethod
    def _extraction_to_dict(ext: ProbeExtraction) -> dict:
        return {
            "brand_mentioned": ext.brand_mentioned,
            "rank_position": ext.rank_position,
            "recommends_competitor": ext.recommends_competitor,
            "competitors_mentioned": ext.competitors_mentioned,
            "info_is_accurate": ext.info_is_accurate,
            "negative_detected": ext.negative_detected,
            "cited_sources": ext.cited_sources,
            "response_sentiment": ext.response_sentiment,
        }

    # ════════════════════════════════════════════════════════════
    # Question generation
    # ════════════════════════════════════════════════════════════

    def _generate_question_set(self, task: DetectionTask,
                                identity: EnterpriseIdentityProfile | None,
                                competitor_names: list[str]) -> list[dict]:
        """Generate the complete question set for probing.

        Combines: task keywords × question templates × target models × rounds
        """
        company_name = identity.company_name if identity else "未命名企业"
        industry = identity.industry if identity and hasattr(identity, 'industry') else ""
        main_business = task.keywords[0].get("word", "") if task.keywords else ""
        rival_name = competitor_names[0] if competitor_names else f"{industry}行业头部企业"

        questions = []
        for kw in task.keywords:
            word = kw.get("word", "")
            kw_type = kw.get("type", "broad")
            templates = PROBE_QUESTION_TEMPLATES.get(kw_type,
                                                      PROBE_QUESTION_TEMPLATES["broad"])

            for model in task.target_models:
                for round_num in range(1, 4):  # 3 rounds per model per keyword
                    template_idx = (hash(f"{model}:{word}:{round_num}") % len(templates))
                    q_text = templates[template_idx].format(
                        company_name=company_name,
                        industry=industry or word,
                        main_business=main_business or word,
                        rival_name=rival_name,
                    )
                    questions.append({
                        "model": model,
                        "keyword": word,
                        "keyword_type": kw_type,
                        "round": round_num,
                        "question": q_text,
                    })

        return questions

    def _build_known_facts(self, identity: EnterpriseIdentityProfile) -> str:
        """Build a known-facts string from the identity profile for consistency checking."""
        facts = []
        if identity.company_name:
            facts.append(f"企业名称: {identity.company_name}")
        if identity.business_license_number:
            facts.append(f"统一社会信用代码: {identity.business_license_number}")
        if identity.legal_representative:
            facts.append(f"法定代表人: {identity.legal_representative}")
        if identity.registered_capital:
            facts.append(f"注册资本: {identity.registered_capital}")
        if identity.business_scope:
            facts.append(f"经营范围: {identity.business_scope}")
        if identity.establishment_date:
            facts.append(f"成立日期: {identity.establishment_date.isoformat()}")
        if identity.official_website:
            facts.append(f"官方网站: {identity.official_website}")
        if identity.certifications:
            certs = [f"{c.get('name', '')}(有效期至{c.get('valid_until', '未知')})"
                      for c in identity.certifications]
            facts.append(f"资质证书: {', '.join(certs)}")
        if identity.patents_count:
            facts.append(f"专利数量: {identity.patents_count}")
        if identity.trademarks_count:
            facts.append(f"商标数量: {identity.trademarks_count}")
        if identity.offline_locations_count:
            facts.append(f"线下网点数: {identity.offline_locations_count}")

        return "\n".join(facts)

    # ════════════════════════════════════════════════════════════
    # Query methods
    # ════════════════════════════════════════════════════════════

    async def get_execution(self, task_id: uuid.UUID) -> ProbeExecutionLog | None:
        """Get the latest execution log for a task."""
        result = await self.db.execute(
            select(ProbeExecutionLog).where(
                ProbeExecutionLog.customer_id == self.customer_id,
                ProbeExecutionLog.task_id == task_id,
            ).order_by(ProbeExecutionLog.created_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_raw_responses(self, task_id: uuid.UUID,
                                  model_name: str | None = None,
                                  limit: int = 100) -> list[ModelProbeResponse]:
        """Get raw probe responses for a task."""
        query = select(ModelProbeResponse).where(
            ModelProbeResponse.customer_id == self.customer_id,
            ModelProbeResponse.task_id == task_id,
        )
        if model_name:
            query = query.where(ModelProbeResponse.model_name == model_name)
        result = await self.db.execute(
            query.order_by(ModelProbeResponse.model_name, ModelProbeResponse.probed_at).limit(limit)
        )
        return list(result.scalars().all())

    async def get_extractions(self, task_id: uuid.UUID) -> list[ProbeExtraction]:
        """Get all structured extractions for a task."""
        result = await self.db.execute(
            select(ProbeExtraction).where(
                ProbeExtraction.customer_id == self.customer_id,
                ProbeExtraction.task_id == task_id,
            )
        )
        return list(result.scalars().all())

    async def get_statistics(self, task_id: uuid.UUID,
                               model_name: str | None = None) -> list[ProbeStatistics]:
        """Get statistics for a task."""
        query = select(ProbeStatistics).where(
            ProbeStatistics.customer_id == self.customer_id,
            ProbeStatistics.task_id == task_id,
        )
        if model_name:
            query = query.where(ProbeStatistics.model_name == model_name)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def correct_extraction(self, extraction_id: uuid.UUID,
                                   corrected_by: uuid.UUID,
                                   corrections: dict,
                                   notes: str = "") -> ProbeExtraction:
        """Apply human correction to an extraction result."""
        result = await self.db.execute(
            select(ProbeExtraction).where(
                ProbeExtraction.id == extraction_id,
                ProbeExtraction.customer_id == self.customer_id,
            )
        )
        ext = result.scalar_one_or_none()
        if not ext:
            raise NotFoundException("ProbeExtraction", str(extraction_id))

        corrected_fields = []
        for field, new_value in corrections.items():
            if hasattr(ext, field):
                old_value = getattr(ext, field)
                setattr(ext, field, new_value)
                corrected_fields.append({
                    "field": field,
                    "old_value": old_value,
                    "new_value": new_value,
                })

        ext.is_human_corrected = True
        ext.corrected_by = corrected_by
        ext.corrected_at = datetime.now(timezone.utc)
        ext.correction_notes = notes
        ext.corrected_fields = corrected_fields
        await self.db.flush()
        return ext

    # ════════════════════════════════════════════════════════════
    # Helpers
    # ════════════════════════════════════════════════════════════

    async def _get_task(self, task_id: uuid.UUID) -> DetectionTask:
        result = await self.db.execute(
            select(DetectionTask).where(
                DetectionTask.id == task_id,
                DetectionTask.customer_id == self.customer_id,
            )
        )
        task = result.scalar_one_or_none()
        if not task:
            raise NotFoundException("DetectionTask", str(task_id))
        return task

    async def _get_identity(self) -> EnterpriseIdentityProfile | None:
        result = await self.db.execute(
            select(EnterpriseIdentityProfile).where(
                EnterpriseIdentityProfile.customer_id == self.customer_id,
            ).order_by(EnterpriseIdentityProfile.updated_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_competitor_names(self, task: DetectionTask) -> list[str]:
        if not task.competitor_ids:
            return []
        result = await self.db.execute(
            select(Competitor.name).where(
                Competitor.id.in_(task.competitor_ids),
                Competitor.customer_id == self.customer_id,
            )
        )
        return [row[0] for row in result.all()]

    async def close(self):
        await self.parser.close()

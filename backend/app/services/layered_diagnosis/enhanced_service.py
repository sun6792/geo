"""P6: Enhanced Diagnosis Service — Agent 2 layered diagnosis orchestration.

Integrates:
- ThreeLayerDiagnosisEngine for scoring + gap detection
- GapToBriefConverter for Agent 3 linkage
- DeepSeek-powered intelligent attribution
- Auto-trigger from Agent 1 detection completion
- Historical score comparison
"""

import uuid
from datetime import datetime, timezone, date, timedelta
from typing import Optional

from sqlalchemy import func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.agent import (
    DetectionTask, DetectionResult, DiagnosisReport, FiveDimScore,
    SourceVerification, SentimentResult, Competitor,
)
from app.models.customer import Customer
from app.models.identity import EnterpriseIdentityProfile
from app.models.knowledge_base import KbAsset
from app.models.publish import WeeklyReview
from app.core.exceptions import NotFoundException, ValidationException
from app.core.pagination import PaginationParams

from app.services.layered_diagnosis.three_layer_engine import (
    ThreeLayerDiagnosisEngine, FiveDimResult, GapItem,
)
from app.services.layered_diagnosis.brief_converter import GapToBriefConverter
from app.services.layered_diagnosis.models import (
    DiagnosisGap, GapToBriefMapping, ScoreHistory, DiagnosisRule,
)


class EnhancedDiagnosisService:
    """Agent 2: Three-layer precise diagnosis + gap checklist + Agent 3 linkage.

    Usage:
        service = EnhancedDiagnosisService(db, customer_id)
        report = await service.run_full_diagnosis(generated_by=user_id)
        gaps = await service.get_gap_checklist(report.id)
        # One-click: gaps → Agent 3 briefs
        briefs = await service.convert_gaps_to_briefs(gap_ids, company_name, industry)
    """

    def __init__(self, db: AsyncSession, customer_id: uuid.UUID):
        self.db = db
        self.customer_id = customer_id
        self.api_key = settings.OPENAI_API_KEY or ""
        self.engine = ThreeLayerDiagnosisEngine(self.api_key)
        self.brief_converter = GapToBriefConverter(self.api_key)

    # ════════════════════════════════════════════════════════════
    # Main: Full diagnosis pipeline
    # ════════════════════════════════════════════════════════════

    async def run_full_diagnosis(self,
                                   generated_by: uuid.UUID,
                                   detection_task_id: uuid.UUID | None = None,
                                   ) -> dict:
        """Execute the complete Agent 2 diagnosis pipeline.

        1. Pull Agent 1 data (detection results, identity, sentiment, competitors)
        2. Scan KB asset status
        3. Run three-layer diagnosis engine (rule-based + DeepSeek attribution)
        4. Persist DiagnosisReport, FiveDimScore, ScoreHistory, DiagnosisGap
        5. Return complete diagnosis result

        If detection_task_id is provided, uses that task's results.
        Otherwise uses all available detection data.
        """
        today = date.today()

        # ── Dedup: check if report already exists for today ────
        existing = (await self.db.execute(
            select(DiagnosisReport).where(
                DiagnosisReport.customer_id == self.customer_id,
                func.date(DiagnosisReport.created_at) == today,
            )
        )).scalars().all()
        if existing:
            latest = existing[0]
            # Return existing report data instead of creating duplicate
            gap_count = (await self.db.execute(
                select(func.count(DiagnosisGap.id)).where(
                    DiagnosisGap.diagnosis_report_id == latest.id
                )
            )).scalar() or 0
            urgent = (await self.db.execute(
                select(func.count(DiagnosisGap.id)).where(
                    DiagnosisGap.diagnosis_report_id == latest.id,
                    DiagnosisGap.priority == "urgent",
                )
            )).scalar() or 0
            return {
                "report_id": str(latest.id),
                "total_score": latest.report_json.get("total_score", 0) if latest.report_json else 0,
                "identity_score": latest.report_json.get("identity_score", 0) if latest.report_json else 0,
                "basic_asset_score": latest.report_json.get("basic_asset_score", 0) if latest.report_json else 0,
                "marketing_asset_score": latest.report_json.get("marketing_asset_score", 0) if latest.report_json else 0,
                "multimodal_asset_score": latest.report_json.get("multimodal_asset_score", 0) if latest.report_json else 0,
                "sentiment_score": latest.report_json.get("sentiment_score", 0) if latest.report_json else 0,
                "summary": latest.summary or "已有今日报告",
                "strengths": latest.report_json.get("strengths", []) if latest.report_json else [],
                "weaknesses": latest.report_json.get("weaknesses", []) if latest.report_json else [],
                "gaps_count": gap_count,
                "urgent_gaps": urgent,
                "important_gaps": gap_count - urgent,
                "duplicate": True,
            }

        # ── 1. Pull Agent 1 data ───────────────────────────────
        # Identity profile
        identity_data = await self._load_identity_data()

        # Detection results
        detection_data = await self._load_detection_data(detection_task_id)

        # Competitor summary
        competitor_data = await self._load_competitor_data()

        # Sentiment data
        sentiment_data = await self._load_sentiment_data()

        # KB status
        kb_status = await self._scan_kb_status()

        # Customer info
        customer = await self._get_customer()
        company_name = customer.company_name or customer.name
        industry = customer.industry or "未指定行业"

        # ── 2. Run three-layer diagnosis ───────────────────────
        five_dim_result, gap_items = await self.engine.run_diagnosis(
            company_name=company_name,
            industry=industry,
            identity_data=identity_data,
            detection_results=detection_data,
            kb_status=kb_status,
            competitor_data=competitor_data,
            sentiment_data=sentiment_data,
        )

        # ── 3. Persist diagnosis report ────────────────────────
        # Try to get task name for meaningful title
        task_name = ""
        if detection_task_id:
            from app.models.agent import DetectionTask as DT
            task_r = await self.db.execute(select(DT).where(DT.id == detection_task_id))
            task_obj = task_r.scalar_one_or_none()
            if task_obj:
                task_name = f" - {task_obj.name}"
        report = DiagnosisReport(
            customer_id=self.customer_id,
            title=f"【{company_name}】AI引流诊断报告{task_name} {today.strftime('%m月%d日')}",
            report_type="layered",
            diagnosis_period_start=today - timedelta(days=7),
            diagnosis_period_end=today,
            status="published",
            summary=five_dim_result.summary,
            common_gaps=five_dim_result.weaknesses[:5],
            platform_gaps=[],
            recommendations=[],
            report_json={
                "engine_version": "2.0",
                "identity_score": five_dim_result.identity.score,
                "basic_asset_score": five_dim_result.basic_asset.score,
                "marketing_asset_score": five_dim_result.marketing_asset.score,
                "multimodal_asset_score": five_dim_result.multimodal_asset.score,
                "sentiment_score": five_dim_result.sentiment.score,
                "total_score": five_dim_result.total_score,
                "strengths": five_dim_result.strengths,
                "weaknesses": five_dim_result.weaknesses,
            },
            generated_by=generated_by,
        )
        self.db.add(report)
        await self.db.flush()

        # ── 4. Persist five-dim scores ─────────────────────────
        dims = [
            ("identity", five_dim_result.identity),
            ("basic_asset", five_dim_result.basic_asset),
            ("marketing_asset", five_dim_result.marketing_asset),
            ("multimodal_asset", five_dim_result.multimodal_asset),
            ("sentiment", five_dim_result.sentiment),
        ]
        for dim_name, dim in dims:
            # Map to existing FiveDimScore fields
            self.db.add(FiveDimScore(
                customer_id=self.customer_id,
                diagnosis_report_id=report.id,
                model_name=None,
                identity_score=dim.score if dim_name in ("identity", "basic_asset") else 0,
                source_score=dim.score if dim_name == "identity" else 0,
                content_depth_score=dim.score if dim_name == "marketing_asset" else 0,
                content_freshness_score=dim.score if dim_name == "multimodal_asset" else 0,
                cross_validation_score=dim.score if dim_name == "sentiment" else 0,
                total_score=five_dim_result.total_score,
                score_metadata={
                    "dimension": dim_name,
                    "layer": dim.layer,
                    "status": dim.status,
                    "key_issues": dim.key_issues,
                },
            ))

        # ── 5. Persist gaps ────────────────────────────────────
        for gap in gap_items:
            self.db.add(DiagnosisGap(
                customer_id=self.customer_id,
                diagnosis_report_id=report.id,
                layer=gap.layer,
                category=gap.category,
                gap_name=gap.name,
                description=gap.description,
                impact_weight=gap.impact_weight,
                impact_explanation=gap.impact_explanation,
                affected_models=gap.affected_models,
                fix_recommendation=gap.fix_recommendation,
                content_type_needed=gap.content_type_needed,
                target_keywords=gap.target_keywords,
                estimated_impact=gap.estimated_impact,
                priority=gap.priority,
                priority_reason=gap.priority_reason,
            ))

        # ── 6. Persist score history ───────────────────────────
        previous = await self._get_previous_scores()
        self.db.add(ScoreHistory(
            customer_id=self.customer_id,
            diagnosis_report_id=report.id,
            identity_score=five_dim_result.identity.score,
            basic_asset_score=five_dim_result.basic_asset.score,
            marketing_asset_score=five_dim_result.marketing_asset.score,
            multimodal_asset_score=five_dim_result.multimodal_asset.score,
            sentiment_score=five_dim_result.sentiment.score,
            total_score=five_dim_result.total_score,
            urgent_gaps=sum(1 for g in gap_items if g.priority == "urgent"),
            important_gaps=sum(1 for g in gap_items if g.priority == "important"),
            long_term_gaps=sum(1 for g in gap_items if g.priority == "long_term"),
            total_score_change=round(five_dim_result.total_score - previous["total"], 1)
                                if previous else None,
            identity_score_change=round(five_dim_result.identity.score - previous["identity"], 1)
                                    if previous else None,
            gaps_resolved_since_last=None,
        ))

        await self.db.flush()

        return {
            "report_id": str(report.id),
            "total_score": five_dim_result.total_score,
            "identity_score": five_dim_result.identity.score,
            "basic_asset_score": five_dim_result.basic_asset.score,
            "marketing_asset_score": five_dim_result.marketing_asset.score,
            "multimodal_asset_score": five_dim_result.multimodal_asset.score,
            "sentiment_score": five_dim_result.sentiment.score,
            "summary": five_dim_result.summary,
            "strengths": five_dim_result.strengths,
            "weaknesses": five_dim_result.weaknesses,
            "gaps_count": len(gap_items),
            "urgent_gaps": sum(1 for g in gap_items if g.priority == "urgent"),
            "important_gaps": sum(1 for g in gap_items if g.priority == "important"),
        }

    # ════════════════════════════════════════════════════════════
    # Gap operations
    # ════════════════════════════════════════════════════════════

    async def get_gap_checklist(self, report_id: uuid.UUID,
                                  layer: str | None = None,
                                  priority: str | None = None) -> list[DiagnosisGap]:
        """Get the gap checklist for a diagnosis report, with optional filters."""
        query = select(DiagnosisGap).where(
            DiagnosisGap.customer_id == self.customer_id,
            DiagnosisGap.diagnosis_report_id == report_id,
        )
        if layer:
            query = query.where(DiagnosisGap.layer == layer)
        if priority:
            query = query.where(DiagnosisGap.priority == priority)

        result = await self.db.execute(
            query.order_by(
                DiagnosisGap.priority == "urgent",
                DiagnosisGap.priority == "important",
                DiagnosisGap.impact_weight.desc(),
            )
        )
        return list(result.scalars().all())

    async def add_manual_gap(self, report_id: uuid.UUID, data: dict,
                               created_by: uuid.UUID) -> DiagnosisGap:
        """Manually add a gap to the checklist."""
        gap = DiagnosisGap(
            customer_id=self.customer_id,
            diagnosis_report_id=report_id,
            is_manual=True,
            created_by=created_by,
            **{k: v for k, v in data.items() if hasattr(DiagnosisGap, k)},
        )
        self.db.add(gap)
        await self.db.flush()
        return gap

    async def update_gap(self, gap_id: uuid.UUID, data: dict) -> DiagnosisGap:
        """Update a gap (status change, priority adjustment, etc.)."""
        result = await self.db.execute(
            select(DiagnosisGap).where(
                DiagnosisGap.id == gap_id,
                DiagnosisGap.customer_id == self.customer_id,
            )
        )
        gap = result.scalar_one_or_none()
        if not gap:
            raise NotFoundException("DiagnosisGap", str(gap_id))
        for k, v in data.items():
            if hasattr(gap, k):
                setattr(gap, k, v)
        await self.db.flush()
        return gap

    async def delete_gap(self, gap_id: uuid.UUID) -> None:
        """Delete a gap from the checklist."""
        result = await self.db.execute(
            select(DiagnosisGap).where(
                DiagnosisGap.id == gap_id,
                DiagnosisGap.customer_id == self.customer_id,
            )
        )
        gap = result.scalar_one_or_none()
        if not gap:
            raise NotFoundException("DiagnosisGap", str(gap_id))
        await self.db.delete(gap)
        await self.db.flush()

    # ════════════════════════════════════════════════════════════
    # Gap → Brief conversion (Agent 2 → Agent 3 linkage)
    # ════════════════════════════════════════════════════════════

    async def convert_gaps_to_briefs(self,
                                      gap_ids: list[uuid.UUID],
                                      created_by: uuid.UUID) -> list[dict]:
        """One-click: convert selected gaps into Agent 3 content briefs.

        Each gap → tailored BriefSpec → ContentBrief record → ready for generation.
        This is the critical Agent 2→Agent 3 handoff.
        """
        from app.models.content import ContentBrief

        customer = await self._get_customer()
        company_name = customer.company_name or customer.name
        industry = customer.industry or ""

        # Load gaps
        gaps = (await self.db.execute(
            select(DiagnosisGap).where(
                DiagnosisGap.id.in_(gap_ids),
                DiagnosisGap.customer_id == self.customer_id,
            )
        )).scalars().all()

        if not gaps:
            raise ValidationException("No valid gaps found")

        # Convert each gap to a brief spec
        gap_dicts = [
            {
                "name": g.gap_name, "description": g.description,
                "layer": g.layer, "impact_weight": g.impact_weight,
                "impact_explanation": g.impact_explanation or "",
                "fix_recommendation": g.fix_recommendation or "",
                "category": g.category,
                "target_keywords": g.target_keywords,
                "priority": g.priority,
                "content_type_needed": g.content_type_needed,
            }
            for g in gaps
        ]

        specs = await self.brief_converter.convert_batch(
            gap_dicts, company_name, industry
        )

        # Create ContentBrief records
        created_briefs = []
        for gap, spec in zip(gaps, specs):
            if not isinstance(spec, type(gap_dicts[0])):  # It's a BriefSpec
                brief = ContentBrief(
                    customer_id=self.customer_id,
                    title=spec.title,
                    content_type=spec.content_type,
                    tone_style=spec.tone_style,
                    target_audience=spec.target_audience,
                    target_keywords=spec.target_keywords,
                    word_count_target=spec.word_count_target,
                    description=spec.description,
                    source_kb_asset_ids=[],
                    status="draft",
                    priority={"urgent": 10, "important": 5, "long_term": 1}.get(gap.priority, 5),
                    created_by=created_by,
                )
                self.db.add(brief)
                await self.db.flush()

                # Link gap to brief
                self.db.add(GapToBriefMapping(
                    customer_id=self.customer_id,
                    gap_id=gap.id,
                    brief_id=brief.id,
                    auto_generated=True,
                    created_by=created_by,
                ))

                # Mark gap as converted
                gap.converted_to_brief = True
                gap.linked_brief_id = brief.id

                created_briefs.append({
                    "gap_id": str(gap.id),
                    "brief_id": str(brief.id),
                    "title": brief.title,
                    "content_type": brief.content_type,
                    "priority": brief.priority,
                })

        await self.db.flush()
        return created_briefs

    # ════════════════════════════════════════════════════════════
    # History & trends
    # ════════════════════════════════════════════════════════════

    async def get_score_history(self, limit: int = 12) -> list[ScoreHistory]:
        """Get historical score records for trend analysis."""
        result = await self.db.execute(
            select(ScoreHistory).where(
                ScoreHistory.customer_id == self.customer_id,
            ).order_by(ScoreHistory.recorded_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def get_score_trends(self) -> dict:
        """Get score trends with change calculations."""
        history = await self.get_score_history(12)
        if not history:
            return {"message": "暂无历史数据", "data": []}

        trends = []
        for h in reversed(history):
            trends.append({
                "date": h.recorded_at.isoformat(),
                "total": h.total_score,
                "identity": h.identity_score,
                "basic_asset": h.basic_asset_score,
                "marketing_asset": h.marketing_asset_score,
                "multimodal_asset": h.multimodal_asset_score,
                "sentiment": h.sentiment_score,
                "urgent_gaps": h.urgent_gaps,
                "change": h.total_score_change,
            })

        latest = history[0]
        return {
            "latest": {
                "total_score": latest.total_score,
                "identity_score": latest.identity_score,
                "basic_asset_score": latest.basic_asset_score,
                "marketing_asset_score": latest.marketing_asset_score,
                "multimodal_asset_score": latest.multimodal_asset_score,
                "sentiment_score": latest.sentiment_score,
            },
            "trends": trends,
            "overall_change": latest.total_score_change,
        }

    # ════════════════════════════════════════════════════════════
    # Diagnosis rules (configurable)
    # ════════════════════════════════════════════════════════════

    async def list_rules(self, industry: str | None = None) -> list[DiagnosisRule]:
        """List active diagnosis rules (global + industry-specific)."""
        query = select(DiagnosisRule).where(
            DiagnosisRule.is_active == True,
            (DiagnosisRule.customer_id == self.customer_id) |
            (DiagnosisRule.customer_id.is_(None)),
        )
        if industry:
            query = query.where(
                (DiagnosisRule.industry == industry) | (DiagnosisRule.industry.is_(None))
            )
        result = await self.db.execute(query.order_by(DiagnosisRule.sort_order))
        return list(result.scalars().all())

    # ════════════════════════════════════════════════════════════
    # Data loading helpers
    # ════════════════════════════════════════════════════════════

    async def _load_identity_data(self) -> dict:
        result = await self.db.execute(
            select(EnterpriseIdentityProfile).where(
                EnterpriseIdentityProfile.customer_id == self.customer_id,
            ).order_by(EnterpriseIdentityProfile.updated_at.desc()).limit(1)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            return {"trust_score": 20, "message": "身份档案未建立"}
        return {
            "trust_score": profile.trust_score,
            "business_license_match": profile.business_license_verified,
            "encyclopedia_entry_exists": len(profile.encyclopedia_entries) > 0,
            "blue_v_verified": profile.blue_v_verified,
            "blue_v_platforms": profile.blue_v_platforms,
            "certification_count": profile.certification_count,
            "patents_count": profile.patents_count,
            "offline_locations_count": profile.offline_locations_count,
            "issues": profile.business_license_issues,
        }

    async def _load_detection_data(self, task_id: uuid.UUID | None = None) -> list[dict]:
        if task_id:
            results = (await self.db.execute(
                select(DetectionResult).where(
                    DetectionResult.customer_id == self.customer_id,
                    DetectionResult.task_id == task_id,
                )
            )).scalars().all()
        else:
            results = (await self.db.execute(
                select(DetectionResult).where(
                    DetectionResult.customer_id == self.customer_id,
                ).order_by(DetectionResult.detected_at.desc()).limit(200)
            )).scalars().all()

        # Aggregate by model
        model_data = {}
        for r in results:
            if r.model_name not in model_data:
                model_data[r.model_name] = {"mention_rate": 0, "total": 0,
                                              "brand_mention_rate": 0, "competitor_preference_rate": 0}
            md = model_data[r.model_name]
            md["total"] += 1
            if r.brand_mentioned:
                md["mention_rate"] = (md.get("mention_rate", 0) + 1)
            # competitor pref from metadata
            if r.result_metadata.get("recommends_competitor"):
                md["competitor_preference_rate"] = md.get("competitor_preference_rate", 0) + 1

        for model, data in model_data.items():
            data["mention_rate"] = round(data["mention_rate"] / data["total"] * 100, 1) if data["total"] else 0
            data["competitor_preference_rate"] = round(
                data.get("competitor_preference_rate", 0) / data["total"] * 100, 1) if data["total"] else 0

        return [{"model_name": k, **v} for k, v in model_data.items()]

    async def _load_competitor_data(self) -> dict:
        result = await self.db.execute(
            select(Competitor).where(
                Competitor.customer_id == self.customer_id,
                Competitor.is_active == True,
            )
        )
        comps = list(result.scalars().all())
        return {
            "competitors": [{"name": c.name, "industry": c.industry} for c in comps],
            "count": len(comps),
        }

    async def _load_sentiment_data(self) -> dict:
        sentiments = (await self.db.execute(
            select(SentimentResult).where(
                SentimentResult.customer_id == self.customer_id,
            )
        )).scalars().all()

        pos = sum(1 for s in sentiments if s.sentiment == "positive")
        neg = sum(1 for s in sentiments if s.sentiment == "negative")
        return {
            "total": len(sentiments),
            "positive": pos,
            "neutral": len(sentiments) - pos - neg,
            "negative": neg,
            "alert_count": sum(1 for s in sentiments if s.is_alert),
        }

    async def _scan_kb_status(self) -> dict:
        """Scan KB assets grouped by type for gap analysis."""
        assets = (await self.db.execute(
            select(KbAsset).where(
                KbAsset.customer_id == self.customer_id,
                KbAsset.is_latest == True,
                KbAsset.status == "published",
            )
        )).scalars().all()

        basic_fields = ["企业简介", "产品参数", "资质证书", "联系方式"]
        marketing_fields = ["行业关键词", "客户案例", "差异化优势", "竞品分析", "避坑指南"]
        multimodal_fields = ["产品图片", "技术白皮书", "短视频", "项目案例", "客户评价"]

        gaps = {
            "basic": {"has": sum(1 for a in assets if a.asset_type == "basic"),
                       "missing_fields": basic_fields,
                       "severity": "adequate"},
            "marketing": {"has": sum(1 for a in assets if a.asset_type == "marketing"),
                           "missing_fields": marketing_fields,
                           "severity": "adequate"},
            "multimodal": {"has": sum(1 for a in assets if a.asset_type == "multimodal"),
                            "missing_fields": multimodal_fields,
                            "severity": "adequate"},
        }

        for asset_type, info in gaps.items():
            has = info["has"]
            if has == 0:
                info["severity"] = "severe"
            elif has < 2:
                info["severity"] = "partial"
            else:
                info["severity"] = "adequate"

        return gaps

    async def _get_customer(self) -> Customer:
        result = await self.db.execute(
            select(Customer).where(Customer.id == self.customer_id)
        )
        customer = result.scalar_one_or_none()
        if not customer:
            raise NotFoundException("Customer", str(self.customer_id))
        return customer

    async def _get_previous_scores(self) -> dict | None:
        """Get the most recent ScoreHistory for change calculation."""
        result = await self.db.execute(
            select(ScoreHistory).where(
                ScoreHistory.customer_id == self.customer_id,
            ).order_by(ScoreHistory.recorded_at.desc()).limit(1)
        )
        prev = result.scalar_one_or_none()
        if not prev:
            return None
        return {
            "total": prev.total_score,
            "identity": prev.identity_score,
            "basic_asset": prev.basic_asset_score,
            "marketing_asset": prev.marketing_asset_score,
            "multimodal_asset": prev.multimodal_asset_score,
            "sentiment": prev.sentiment_score,
        }

    async def close(self):
        await self.engine.close()
        await self.brief_converter.close()

"""Agent 2: Diagnosis & Analysis Service — per-model diagnosis, 5-dim scoring, optimization tasks."""

import uuid
from datetime import datetime, timezone, date, timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.core.pagination import PaginationParams
from app.models.agent import DiagnosisReport, FiveDimScore, OptimizationItem


class DiagnosisService:
    """Agent 2: Gap analysis, five-dimension scoring, and automated optimization task generation."""

    def __init__(self, db: AsyncSession, customer_id: uuid.UUID):
        self.db = db
        self.customer_id = customer_id

    # ── Diagnosis Reports ─────────────────────────────────────

    async def list_reports(self, pagination: PaginationParams) -> tuple[list[DiagnosisReport], int]:
        query = select(DiagnosisReport).where(DiagnosisReport.customer_id == self.customer_id)
        count_q = select(func.count(DiagnosisReport.id)).where(DiagnosisReport.customer_id == self.customer_id)
        total = (await self.db.execute(count_q)).scalar() or 0
        items = (await self.db.execute(
            query.order_by(DiagnosisReport.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
        )).scalars().all()
        return list(items), total

    async def generate_diagnosis(self, generated_by: uuid.UUID) -> DiagnosisReport:
        """Generate a new diagnosis report based on current detection data and KB state."""
        today = date.today()

        # 1. Scan KB asset gaps
        kb_gaps = await self._scan_kb_gaps()

        # 2. Analyze detection results per model
        model_analysis = await self._analyze_detection_data()

        # 3. Calculate five-dimension scores
        scores = self._calculate_scores(model_analysis, kb_gaps)

        # 4. Build the report
        report = DiagnosisReport(
            customer_id=self.customer_id,
            title=f"GEO诊断报告 — {today.strftime('%Y年%m月%d日')}",
            report_type="overall",
            diagnosis_period_start=today - timedelta(days=7),
            diagnosis_period_end=today,
            status="published",
            summary=self._generate_summary(model_analysis, kb_gaps),
            common_gaps=self._build_common_gaps(kb_gaps),
            platform_gaps=self._build_platform_gaps(model_analysis),
            recommendations=self._build_recommendations(model_analysis, kb_gaps),
            report_json={"scores": scores, "kb_gaps": kb_gaps, "model_analysis": model_analysis},
            generated_by=generated_by,
        )
        self.db.add(report)
        await self.db.flush()

        # 5. Save five-dim scores
        for model_name, score_data in scores.items():
            self.db.add(FiveDimScore(
                customer_id=self.customer_id,
                diagnosis_report_id=report.id,
                model_name=model_name if model_name != "overall" else None,
                identity_score=score_data.get("identity", 0),
                source_score=score_data.get("source", 0),
                content_depth_score=score_data.get("content_depth", 0),
                content_freshness_score=score_data.get("freshness", 0),
                cross_validation_score=score_data.get("cross_validation", 0),
                total_score=score_data.get("total", 0),
            ))

        # 6. Auto-generate optimization tasks
        await self._generate_optimization_tasks(report.id, model_analysis, kb_gaps, generated_by)

        await self.db.flush()
        return report

    async def get_report(self, report_id: uuid.UUID) -> DiagnosisReport:
        result = await self.db.execute(
            select(DiagnosisReport).where(DiagnosisReport.id == report_id, DiagnosisReport.customer_id == self.customer_id)
        )
        r = result.scalar_one_or_none()
        if not r:
            raise NotFoundException("DiagnosisReport", str(report_id))
        return r

    # ── Five-Dim Scores ───────────────────────────────────────

    async def get_scores(self, report_id: uuid.UUID) -> list[FiveDimScore]:
        result = await self.db.execute(
            select(FiveDimScore).where(
                FiveDimScore.customer_id == self.customer_id,
                FiveDimScore.diagnosis_report_id == report_id,
            ).order_by(FiveDimScore.total_score.desc())
        )
        return list(result.scalars().all())

    # ── Optimization Items ───────────────────────────────────

    async def list_optimization_items(self, status: Optional[str] = None,
                                       priority: Optional[str] = None) -> list[OptimizationItem]:
        query = select(OptimizationItem).where(OptimizationItem.customer_id == self.customer_id)
        if status:
            query = query.where(OptimizationItem.status == status)
        if priority:
            query = query.where(OptimizationItem.priority == priority)
        result = await self.db.execute(query.order_by(
            OptimizationItem.priority == "urgent",
            OptimizationItem.priority == "important",
            OptimizationItem.created_at.desc()
        ))
        return list(result.scalars().all())

    async def update_optimization_item(self, item_id: uuid.UUID, data: dict) -> OptimizationItem:
        result = await self.db.execute(
            select(OptimizationItem).where(OptimizationItem.id == item_id, OptimizationItem.customer_id == self.customer_id)
        )
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundException("OptimizationItem", str(item_id))
        for k, v in data.items():
            if v is not None and hasattr(item, k):
                setattr(item, k, v)
        if data.get("status") == "completed":
            item.completed_at = datetime.now(timezone.utc)
        await self.db.flush()
        return item

    # ── Internal Analysis Methods ─────────────────────────────

    async def _scan_kb_gaps(self) -> dict:
        """Scan knowledge base for asset type gaps."""
        from app.models.knowledge_base import KbAsset
        assets = (await self.db.execute(
            select(KbAsset).where(KbAsset.customer_id == self.customer_id, KbAsset.is_latest == True, KbAsset.status == "published")
        )).scalars().all()

        gaps = {
            "basic": {"has": 0, "missing_fields": []},
            "marketing": {"has": 0, "missing_fields": []},
            "multimodal": {"has": 0, "missing_fields": []},
        }

        basic_fields = ["企业简介", "产品参数", "资质证书", "联系方式"]
        marketing_fields = ["行业关键词", "客户案例", "差异化优势", "竞品分析"]
        multimodal_fields = ["产品图片", "技术白皮书", "短视频", "项目案例"]

        for a in assets:
            if a.asset_type in gaps:
                gaps[a.asset_type]["has"] += 1

        if gaps["basic"]["has"] == 0:
            gaps["basic"]["missing_fields"] = basic_fields
            gaps["basic"]["severity"] = "severe"
        elif gaps["basic"]["has"] < 2:
            gaps["basic"]["missing_fields"] = basic_fields[2:]
            gaps["basic"]["severity"] = "partial"
        else:
            gaps["basic"]["severity"] = "adequate"

        if gaps["marketing"]["has"] == 0:
            gaps["marketing"]["missing_fields"] = marketing_fields
            gaps["marketing"]["severity"] = "severe"
        elif gaps["marketing"]["has"] < 2:
            gaps["marketing"]["missing_fields"] = marketing_fields[2:]
            gaps["marketing"]["severity"] = "partial"
        else:
            gaps["marketing"]["severity"] = "adequate"

        if gaps["multimodal"]["has"] == 0:
            gaps["multimodal"]["missing_fields"] = multimodal_fields
            gaps["multimodal"]["severity"] = "severe"
        else:
            gaps["multimodal"]["severity"] = "adequate" if gaps["multimodal"]["has"] >= 2 else "partial"

        return gaps

    async def _analyze_detection_data(self) -> dict:
        """Analyze detection results grouped by model."""
        from app.models.agent import DetectionResult
        results = (await self.db.execute(
            select(DetectionResult).where(DetectionResult.customer_id == self.customer_id)
        )).scalars().all()

        analysis = {}
        for r in results:
            if r.model_name not in analysis:
                analysis[r.model_name] = {"total": 0, "mentioned": 0, "high_rec": 0, "cited_sources": set()}
            analysis[r.model_name]["total"] += 1
            if r.brand_mentioned:
                analysis[r.model_name]["mentioned"] += 1
            if r.recommendation_level == "high":
                analysis[r.model_name]["high_rec"] += 1
            for s in r.cited_sources:
                analysis[r.model_name]["cited_sources"].add(s.get("name", ""))

        for model, data in analysis.items():
            data["mention_rate"] = round(data["mentioned"] / data["total"] * 100, 1) if data["total"] > 0 else 0
            data["cited_sources"] = list(data["cited_sources"])

        return analysis

    def _calculate_scores(self, model_analysis: dict, kb_gaps: dict) -> dict:
        """Calculate five-dimension scores (0-100) for each model and overall."""
        scores = {}
        for model, data in model_analysis.items():
            identity = min(100, 20 + (40 if model_analysis else 0) + kb_gaps.get("basic", {}).get("has", 0) * 10)
            source = min(100, 30 + len(data.get("cited_sources", [])) * 15)
            content_depth = min(100, 20 + (30 if data.get("mention_rate", 0) > 30 else 0) + kb_gaps.get("marketing", {}).get("has", 0) * 10)
            freshness = min(100, 40 + (30 if data.get("mention_rate", 0) > 50 else 0))
            cross = min(100, 10 + len(data.get("cited_sources", [])) * 20)
            total = round((identity + source + content_depth + freshness + cross) / 5, 1)

            scores[model] = {
                "identity": identity, "source": source, "content_depth": content_depth,
                "freshness": freshness, "cross_validation": cross, "total": total,
            }

        # Overall score
        if scores:
            overall = {
                "identity": round(sum(s["identity"] for s in scores.values()) / len(scores), 1),
                "source": round(sum(s["source"] for s in scores.values()) / len(scores), 1),
                "content_depth": round(sum(s["content_depth"] for s in scores.values()) / len(scores), 1),
                "freshness": round(sum(s["freshness"] for s in scores.values()) / len(scores), 1),
                "cross_validation": round(sum(s["cross_validation"] for s in scores.values()) / len(scores), 1),
            }
            overall["total"] = round(sum(overall.values()) / 5, 1)
            scores["overall"] = overall

        return scores

    def _generate_summary(self, model_analysis: dict, kb_gaps: dict) -> str:
        lines = []
        lines.append(f"本轮诊断覆盖 {len(model_analysis)} 个大模型。")

        severe_gaps = [k for k, v in kb_gaps.items() if v.get("severity") == "severe"]
        if severe_gaps:
            lines.append(f"知识库{', '.join(severe_gaps)}资产严重缺失，建议优先补全。")

        low_models = [m for m, d in model_analysis.items() if d.get("mention_rate", 0) < 20]
        if low_models:
            lines.append(f"{', '.join(low_models)} 品牌曝光率低于20%，需要重点优化。")

        return " ".join(lines)

    def _build_common_gaps(self, kb_gaps: dict) -> list:
        gaps = []
        for asset_type, info in kb_gaps.items():
            if info.get("severity") in ("severe", "partial"):
                gaps.append({"asset_type": asset_type, "severity": info["severity"], "missing": info.get("missing_fields", [])})
        return gaps

    def _build_platform_gaps(self, model_analysis: dict) -> list:
        gaps = []
        model_ecosystem = {
            "doubao": "头条/抖音生态", "wenxin": "百度/百家号生态", "qianwen": "阿里云/1688生态",
            "yuanbao": "微信/视频号生态", "xinghuo": "政企/期刊生态", "deepseek": "技术社区/开源生态", "kimi": "长文/多源生态",
        }
        for model, data in model_analysis.items():
            if data.get("mention_rate", 0) < 25:
                gaps.append({"model": model, "ecosystem": model_ecosystem.get(model, "未知"), "mention_rate": data["mention_rate"], "gap": f"{model_ecosystem.get(model, '该模型')}内容布局不足"})
        return gaps

    def _build_recommendations(self, model_analysis: dict, kb_gaps: dict) -> list:
        recs = []
        severe = [k for k, v in kb_gaps.items() if v.get("severity") == "severe"]
        if severe:
            recs.append({"priority": "urgent", "action": f"立即补充{', '.join(severe)}资产", "category": "kb_gap"})

        low_models = [(m, d["mention_rate"]) for m, d in model_analysis.items() if d.get("mention_rate", 0) < 30]
        for model, rate in low_models[:3]:
            recs.append({"priority": "important", "action": f"针对{model}创建专属内容，提升曝光率(当前{rate}%)", "category": "content_creation", "target_model": model})

        # Source expansion
        recs.append({"priority": "long_term", "action": "扩展高权重信源覆盖，增加百度百科、行业协会等权威引用", "category": "channel_expansion"})
        return recs

    async def _generate_optimization_tasks(self, report_id: uuid.UUID, model_analysis: dict, kb_gaps: dict, created_by: uuid.UUID):
        """Auto-generate optimization tasks based on diagnosis results."""
        tasks = []

        # KB gap tasks
        for asset_type, info in kb_gaps.items():
            if info.get("severity") == "severe":
                tasks.append(OptimizationItem(
                    customer_id=self.customer_id, diagnosis_report_id=report_id,
                    title=f"补充{asset_type}资产 — {', '.join(info.get('missing_fields', [])[:2])}",
                    description=f"当前{asset_type}资产严重缺失，需要创建基础资产条目",
                    category="kb_gap", priority="urgent", created_by=created_by,
                ))

        # Content creation tasks for low-performing models
        for model, data in model_analysis.items():
            if data.get("mention_rate", 0) < 25:
                tasks.append(OptimizationItem(
                    customer_id=self.customer_id, diagnosis_report_id=report_id,
                    title=f"针对{model}创建优化内容 (当前曝光率{data['mention_rate']}%)",
                    description=f"创建适配{model}模型的内容，提升品牌在该平台的曝光和推荐",
                    category="content_creation", priority="important", target_model=model, created_by=created_by,
                ))

        for t in tasks:
            self.db.add(t)

"""Aggregate all v1 API routers."""

from fastapi import APIRouter

api_v1_router = APIRouter()

# ── Auth ──────────────────────────────────────────────────────
from app.api.v1.auth import router as auth_router
api_v1_router.include_router(auth_router, prefix="/auth")

# ── Customers (platform admin) ────────────────────────────────
from app.api.v1.customers import router as customers_router
api_v1_router.include_router(customers_router, prefix="/customers")

# ── Users & Roles ─────────────────────────────────────────────
from app.api.v1.users import router as users_router
api_v1_router.include_router(users_router, prefix="/users")

from app.api.v1.roles import router as roles_router
api_v1_router.include_router(roles_router, prefix="/roles")

from app.api.v1.permissions import router as permissions_router
api_v1_router.include_router(permissions_router, prefix="/permissions")

# ── Knowledge Base ────────────────────────────────────────────
from app.api.v1.knowledge_base import router as kb_router
api_v1_router.include_router(kb_router, prefix="/kb")

# ── Content Creation ──────────────────────────────────────────
from app.api.v1.content import router as content_router
api_v1_router.include_router(content_router, prefix="/content")

# ── Review Workflow ───────────────────────────────────────────
from app.api.v1.review import router as review_router
api_v1_router.include_router(review_router, prefix="/reviews")

# ── Publishing ────────────────────────────────────────────────
from app.api.v1.publish import router as publish_router
api_v1_router.include_router(publish_router, prefix="/publish")

# ── P1: Agent 1 — Detection ──────────────────────────────────
from app.api.v1.detection import router as detection_router
api_v1_router.include_router(detection_router, prefix="/detection")

# ── P6: Agent 1 — Multi-Model Probe (mounted under /detection/probe) ─
from app.api.v1.multi_model_probe import router as probe_router
api_v1_router.include_router(probe_router)

# ── P6: Agent 1 V3 — LLM Probe Framework (mounted at /detection/v3) ─
from app.api.v1.detection_v3 import router as detection_v3_router
api_v1_router.include_router(detection_v3_router)

# ── P6: Agent 2 — Layered Diagnosis (mounted under /diagnosis/layered) ─
from app.api.v1.layered_diagnosis import router as layered_diag_router
api_v1_router.include_router(layered_diag_router)

# ── P6: Agent 3 — Multi-Model Content (mounted under /content/multi-model) ─
from app.api.v1.multi_model_content import router as mmc_router
api_v1_router.include_router(mmc_router)

# ── P6: Agent 4 — Smart Publish (mounted under /publish/smart) ─
from app.api.v1.publish_enhancements import router as smart_pub_router
api_v1_router.include_router(smart_pub_router)

# ── P6: Agent 5 — Self Evolution (mounted under /weekly-review/evolution) ─
from app.api.v1.self_evolution import router as evolution_router
api_v1_router.include_router(evolution_router)

# ── P6: Unified Pipeline Status (mounted at /pipeline) ─
from app.api.v1.pipeline_status import router as pipeline_router
api_v1_router.include_router(pipeline_router)

# ── P1: Agent 2 — Diagnosis ──────────────────────────────────
from app.api.v1.diagnosis import router as diagnosis_router
api_v1_router.include_router(diagnosis_router, prefix="/diagnosis")

# ── P1: Agent 5 — Weekly Review & Rules ──────────────────────
from app.api.v1.weekly_review import router as wr_router
api_v1_router.include_router(wr_router, prefix="/weekly-review")

# ── P2: Auto Publish ─────────────────────────────────────────
from app.api.v1.auto_publish import router as ap_router
api_v1_router.include_router(ap_router, prefix="/auto-publish")

# ── P2: Semantic Search & Embedding ──────────────────────────
from app.api.v1.semantic_search import router as ss_router
api_v1_router.include_router(ss_router, prefix="/kb")

# ── P6: Unified Enterprise Profile ───────────────────────────
from app.api.v1.enterprise_profile import router as ep_router
api_v1_router.include_router(ep_router)

# ── P2: Batch Ops, Monitoring, Portal ────────────────────────
from app.api.v1.p2_ops import router as p2_router
api_v1_router.include_router(p2_router, prefix="/p2")

# ── P3: SaaS Billing ─────────────────────────────────────────
from app.api.v1.billing import router as billing_router
api_v1_router.include_router(billing_router, prefix="/billing")

# ── P3: Industry Templates ───────────────────────────────────
from app.api.v1.template import router as template_router
api_v1_router.include_router(template_router, prefix="/templates")

# ── P4: Register extended channel adapters ────────────────────
import app.integrations.publish.extended_channels  # noqa: F401 — auto-registers 15+ adapters

# ── P5: Demo Query, Sub-accounts, Payments, Customer Portal ────
from app.api.v1.p5_business import router as p5_router
api_v1_router.include_router(p5_router)

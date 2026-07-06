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

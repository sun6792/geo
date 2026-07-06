"""P3 SaaS Billing API — Plans, Orders, Payments, Quota, Usage."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.core.pagination import PaginationParams, PaginatedResponse
from app.services.billing_service import BillingService

router = APIRouter(tags=["P3: Billing"])


# ── Plans ────────────────────────────────────────────────────────

@router.get("/plans")
async def list_plans(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """List public plans (requires DB session for query)."""
    return await BillingService(db).list_plans()


@router.post("/plans", status_code=201)
async def create_plan(body: dict,
    current_user: dict = Depends(require_permission("billing", "manage")), db: AsyncSession = Depends(get_db)):
    return await BillingService(db).create_plan(body)


@router.patch("/plans/{plan_id}")
async def update_plan(plan_id: uuid.UUID, body: dict,
    current_user: dict = Depends(require_permission("billing", "manage")), db: AsyncSession = Depends(get_db)):
    return await BillingService(db).update_plan(plan_id, body)


# ── Orders ───────────────────────────────────────────────────────

@router.get("/orders", response_model=PaginatedResponse)
async def list_orders(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    svc = BillingService(db, current_user["customer_id"])
    items, total = await svc.list_orders(PaginationParams(page=page, page_size=page_size), status)
    return PaginatedResponse.create(items, total, PaginationParams(page=page, page_size=page_size))


@router.post("/orders", status_code=201)
async def create_order(body: dict,
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    svc = BillingService(db, current_user["customer_id"])
    body["created_by"] = current_user["user_id"]
    return await svc.create_order(body)


@router.post("/orders/{order_id}/confirm-payment")
async def confirm_payment(order_id: uuid.UUID, body: dict = {},
    current_user: dict = Depends(require_permission("billing", "manage")), db: AsyncSession = Depends(get_db)):
    """Confirm payment with cross-tenant validation."""
    svc = BillingService(db, current_user["customer_id"])
    return await svc.confirm_payment(order_id, body.get("transaction_id"))


# ── Quota & Usage ────────────────────────────────────────────────

@router.get("/quota/check")
async def check_quota(usage_type: str = Query(...),
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await BillingService(db, current_user["customer_id"]).check_quota(usage_type)


@router.post("/usage/record")
async def record_usage(body: dict,
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    svc = BillingService(db, current_user["customer_id"])
    return await svc.record_usage(body.get("usage_type", "llm_call"), body.get("count", 1))


@router.get("/usage/stats")
async def get_usage_stats(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await BillingService(db, current_user["customer_id"]).get_usage_stats()


@router.get("/quota/alerts")
async def get_alerts(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await BillingService(db, current_user["customer_id"]).get_alerts()

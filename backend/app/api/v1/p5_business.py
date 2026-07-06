"""P5 APIs: Demo Query, Sub-account Management, Payment Records, Customer Portal."""

import time
import uuid
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.core.pagination import PaginationParams, PaginatedResponse
from app.services.demo_service import DemoService
from app.services.subscription_service import SubscriptionService, CustomerPortalService

router = APIRouter(tags=["P5: Business"])

# ── Simple in-memory IP rate limiter ──────────────────────────
_rate_store: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT = 5   # max calls per minute per IP
_RATE_WINDOW = 60  # seconds


def _check_rate_limit(ip: str) -> bool:
    now = time.time()
    _rate_store[ip] = [t for t in _rate_store[ip] if now - t < _RATE_WINDOW]
    if len(_rate_store[ip]) >= _RATE_LIMIT:
        return False
    _rate_store[ip].append(now)
    return True


# ══════════════════════════════════════════════════════════════
# Public Demo Query (no login required, rate-limited)
# ══════════════════════════════════════════════════════════════

@router.get("/demo/scan_enterprise")
async def demo_scan_enterprise(
    request: Request,
    company_name: str = Query(..., min_length=1, description="企业全称"),
    industry: str = Query("", description="所属行业"),
    main_business: str = Query("", description="主营产品/业务"),
    db: AsyncSession = Depends(get_db),
):
    """Public: full enterprise GEO scan. Auto-discovers rivals from industry. Rate-limited."""
    ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(ip):
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")

    name = company_name.strip()
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="请输入完整企业全称再分析")

    svc = DemoService(db)
    try:
        return await svc.scan_enterprise(company_name=name, industry=industry, main_business=main_business)
    except Exception as e:
        raise HTTPException(status_code=500, detail="当前模型接口繁忙，请30秒后重新查询")


@router.get("/demo/get_chat_log")
async def get_chat_log(
    task_id: str = Query(..., description="分析任务ID"),
    platform: str = Query("", description="平台名称筛选"),
    db: AsyncSession = Depends(get_db),
):
    """Get stored Q&A logs for a demo scan task. Public access for traceability."""
    from sqlalchemy import select
    from app.models.demo_log import DemoChatLog
    query = select(DemoChatLog).where(DemoChatLog.task_id == task_id).order_by(DemoChatLog.platform, DemoChatLog.round)
    if platform:
        query = query.where(DemoChatLog.platform == platform)
    result = await db.execute(query)
    logs = result.scalars().all()
    return [{"id": l.id, "platform": l.platform, "round": l.round,
             "user_prompt": l.user_prompt, "model_reply": l.model_reply,
             "source_urls": l.source_urls, "company_name": l.company_name,
             "is_rival": l.is_rival, "created_at": l.created_at.isoformat()} for l in logs]


# ══════════════════════════════════════════════════════════════
# Sub-Account Management (admin only)
# ══════════════════════════════════════════════════════════════

@router.get("/sub-accounts", response_model=PaginatedResponse)
async def list_sub_accounts(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    svc = SubscriptionService(db, current_user.get("customer_id"))
    items, total = await svc.list_sub_accounts(PaginationParams(page=page, page_size=page_size))
    return PaginatedResponse.create(items, total, PaginationParams(page=page, page_size=page_size))


@router.post("/sub-accounts", status_code=201)
async def create_sub_account(body: dict,
    current_user: dict = Depends(require_permission("subaccount", "create")), db: AsyncSession = Depends(get_db)):
    """Create a customer sub-account. Set customer_id from body or use current user's."""
    customer_id = body.get("customer_id") or current_user["customer_id"]
    svc = SubscriptionService(db, uuid.UUID(customer_id) if isinstance(customer_id, str) else customer_id)
    body["customer_id"] = customer_id
    body["created_by"] = current_user["user_id"]
    account, password = await svc.create_sub_account(body)
    return {"id": str(account.id), "email": account.email, "password": password, "company_name": account.company_name}


@router.post("/sub-accounts/{sub_id}/reset-password")
async def reset_sub_password(sub_id: uuid.UUID,
    current_user: dict = Depends(require_permission("subaccount", "manage")), db: AsyncSession = Depends(get_db)):
    svc = SubscriptionService(db)
    new_pw = await svc.reset_password(sub_id)
    return {"new_password": new_pw}


@router.patch("/sub-accounts/{sub_id}")
async def toggle_sub_account(sub_id: uuid.UUID, body: dict,
    current_user: dict = Depends(require_permission("subaccount", "manage")), db: AsyncSession = Depends(get_db)):
    svc = SubscriptionService(db)
    return await svc.toggle_sub_account(sub_id, body.get("is_active", True))


# ══════════════════════════════════════════════════════════════
# Payment Records
# ══════════════════════════════════════════════════════════════

@router.get("/payment-records", response_model=PaginatedResponse)
async def list_payments(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    svc = SubscriptionService(db, current_user.get("customer_id"))
    items, total = await svc.list_payments(PaginationParams(page=page, page_size=page_size))
    return PaginatedResponse.create(items, total, PaginationParams(page=page, page_size=page_size))


@router.post("/payment-records", status_code=201)
async def create_payment(body: dict,
    current_user: dict = Depends(require_permission("payment", "create")), db: AsyncSession = Depends(get_db)):
    body["recorded_by"] = current_user["user_id"]
    if "customer_id" not in body:
        body["customer_id"] = current_user["customer_id"]
    svc = SubscriptionService(db)
    return await svc.create_payment(body)


@router.post("/payment-records/{payment_id}/create-sub")
async def create_sub_from_payment(payment_id: uuid.UUID, body: dict,
    current_user: dict = Depends(require_permission("subaccount", "create")), db: AsyncSession = Depends(get_db)):
    """One-click: generate customer sub-account from an existing payment record."""
    svc = SubscriptionService(db)
    return await svc.create_sub_from_payment(payment_id, body["email"], current_user["user_id"])


# ══════════════════════════════════════════════════════════════
# Customer Portal (read-only, sub-account access)
# ══════════════════════════════════════════════════════════════

@router.get("/portal/daily-progress")
async def portal_daily_progress(
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Customer portal: today's publishing and ranking progress."""
    if current_user.get("role_type") == "customer_sub":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Use sub-account portal login")
    svc = CustomerPortalService(db, current_user["customer_id"])
    return await svc.get_daily_progress()


@router.get("/portal/weekly-summary")
async def portal_weekly_summary(
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    svc = CustomerPortalService(db, current_user["customer_id"])
    return await svc.get_weekly_summary()


@router.get("/portal/weekly-reviews")
async def portal_weekly_reviews(
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    svc = CustomerPortalService(db, current_user["customer_id"])
    return await svc.get_weekly_reviews()

"""P3 Industry Template & One-Click Setup API."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.services.template_service import TemplateService

router = APIRouter(tags=["P3: Industry Templates"])


@router.get("/templates")
async def list_templates(industry: str = Query(None),
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await TemplateService(db, current_user.get("customer_id")).list_templates(industry)


@router.get("/templates/industries")
async def list_industries(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await TemplateService(db).get_industries()


@router.get("/templates/{template_id}")
async def get_template(template_id: uuid.UUID,
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await TemplateService(db).get_template(template_id)


@router.post("/templates", status_code=201)
async def create_template(body: dict,
    current_user: dict = Depends(require_permission("kb", "create")), db: AsyncSession = Depends(get_db)):
    body["created_by"] = current_user["user_id"]
    return await TemplateService(db, current_user["customer_id"]).create_template(body)


@router.post("/templates/{template_id}/initialize")
async def initialize_from_template(template_id: uuid.UUID,
    current_user: dict = Depends(require_permission("kb", "create")), db: AsyncSession = Depends(get_db)):
    """One-click initialize a customer account from an industry template."""
    svc = TemplateService(db, current_user["customer_id"])
    stats = await svc.initialize_from_template(template_id, current_user["user_id"])
    return {"message": "Initialization complete", "stats": stats}

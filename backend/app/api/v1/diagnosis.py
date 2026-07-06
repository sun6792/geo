"""Agent 2: Diagnosis API — reports, five-dim scores, optimization items."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.core.pagination import PaginationParams, PaginatedResponse
from app.schemas.agent import (
    DiagnosisReportResponse, FiveDimScoreResponse,
    OptimizationItemUpdate, OptimizationItemResponse,
)
from app.services.diagnosis_service import DiagnosisService

router = APIRouter(tags=["Agent 2: Diagnosis"])


# ── Reports ──────────────────────────────────────────────────────

@router.get("/reports", response_model=PaginatedResponse[DiagnosisReportResponse])
async def list_diagnosis_reports(
    page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    svc = DiagnosisService(db, current_user["customer_id"])
    items, total = await svc.list_reports(PaginationParams(page=page, page_size=page_size))
    return PaginatedResponse.create(items, total, PaginationParams(page=page, page_size=page_size))


@router.post("/reports/generate", response_model=DiagnosisReportResponse, status_code=201)
async def generate_diagnosis(
    current_user: dict = Depends(require_permission("diagnosis", "create")), db: AsyncSession = Depends(get_db),
):
    svc = DiagnosisService(db, current_user["customer_id"])
    return await svc.generate_diagnosis(current_user["user_id"])


@router.get("/reports/{report_id}", response_model=DiagnosisReportResponse)
async def get_diagnosis_report(report_id: uuid.UUID,
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await DiagnosisService(db, current_user["customer_id"]).get_report(report_id)


# ── Five-Dim Scores ──────────────────────────────────────────────

@router.get("/reports/{report_id}/scores", response_model=list[FiveDimScoreResponse])
async def get_scores(report_id: uuid.UUID,
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await DiagnosisService(db, current_user["customer_id"]).get_scores(report_id)


# ── Optimization Items ───────────────────────────────────────────

@router.get("/optimization-items", response_model=list[OptimizationItemResponse])
async def list_optimization_items(
    status: str = Query(None), priority: str = Query(None),
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    return await DiagnosisService(db, current_user["customer_id"]).list_optimization_items(status, priority)


@router.patch("/optimization-items/{item_id}", response_model=OptimizationItemResponse)
async def update_optimization_item(item_id: uuid.UUID, body: OptimizationItemUpdate,
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await DiagnosisService(db, current_user["customer_id"]).update_optimization_item(item_id, body.model_dump(exclude_unset=True))

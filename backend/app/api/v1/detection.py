"""Agent 1: Detection API — tasks, results, competitors, source verification, sentiment."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.core.pagination import PaginationParams, PaginatedResponse
from app.schemas.agent import (
    DetectionTaskCreate, DetectionTaskUpdate, DetectionTaskResponse,
    DetectionResultResponse, CompetitorCreate, CompetitorResponse,
    SourceVerificationResponse, SentimentResponse,
)
from app.services.detection_service import DetectionService

router = APIRouter(tags=["Agent 1: Detection"])


# ── Tasks ────────────────────────────────────────────────────────

@router.get("/tasks", response_model=PaginatedResponse[DetectionTaskResponse])
async def list_detection_tasks(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = DetectionService(db, current_user["customer_id"])
    items, total = await svc.list_tasks(PaginationParams(page=page, page_size=page_size))
    return PaginatedResponse.create(items, total, PaginationParams(page=page, page_size=page_size))


@router.post("/tasks", response_model=DetectionTaskResponse, status_code=201)
async def create_detection_task(
    body: DetectionTaskCreate,
    current_user: dict = Depends(require_permission("detection", "create")),
    db: AsyncSession = Depends(get_db),
):
    svc = DetectionService(db, current_user["customer_id"])
    data = body.model_dump()
    data["created_by"] = current_user["user_id"]
    return await svc.create_task(data)


@router.get("/tasks/{task_id}", response_model=DetectionTaskResponse)
async def get_detection_task(task_id: uuid.UUID, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await DetectionService(db, current_user["customer_id"]).get_task(task_id)


@router.patch("/tasks/{task_id}", response_model=DetectionTaskResponse)
async def update_detection_task(task_id: uuid.UUID, body: DetectionTaskUpdate,
    current_user: dict = Depends(require_permission("detection", "update")), db: AsyncSession = Depends(get_db)):
    return await DetectionService(db, current_user["customer_id"]).update_task(task_id, body.model_dump(exclude_unset=True))


@router.delete("/tasks/{task_id}")
async def delete_detection_task(task_id: uuid.UUID,
    current_user: dict = Depends(require_permission("detection", "create")), db: AsyncSession = Depends(get_db)):
    await DetectionService(db, current_user["customer_id"]).delete_task(task_id)
    return {"message": "Task deleted"}


@router.post("/tasks/{task_id}/run")
async def run_detection(task_id: uuid.UUID,
    current_user: dict = Depends(require_permission("detection", "create")), db: AsyncSession = Depends(get_db)):
    svc = DetectionService(db, current_user["customer_id"])
    results = await svc.run_detection(task_id)
    return {"message": f"Detection completed", "results_count": len(results)}


# ── Results ──────────────────────────────────────────────────────

@router.get("/results", response_model=PaginatedResponse[DetectionResultResponse])
async def list_results(
    task_id: uuid.UUID = Query(None), model_name: str = Query(None),
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    svc = DetectionService(db, current_user["customer_id"])
    items, total = await svc.list_results(task_id, model_name, PaginationParams(page=page, page_size=page_size))
    return PaginatedResponse.create(items, total, PaginationParams(page=page, page_size=page_size))


@router.get("/summary")
async def get_detection_summary(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await DetectionService(db, current_user["customer_id"]).get_result_summary()


# ── Competitors ──────────────────────────────────────────────────

@router.get("/competitors", response_model=list[CompetitorResponse])
async def list_competitors(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await DetectionService(db, current_user["customer_id"]).list_competitors()


@router.post("/competitors", response_model=CompetitorResponse, status_code=201)
async def create_competitor(body: CompetitorCreate,
    current_user: dict = Depends(require_permission("detection", "create")), db: AsyncSession = Depends(get_db)):
    data = body.model_dump(); data["created_by"] = current_user["user_id"]
    return await DetectionService(db, current_user["customer_id"]).create_competitor(data)


# ── Source Verification ──────────────────────────────────────────

@router.get("/source-verifications", response_model=list[SourceVerificationResponse])
async def list_source_verifications(is_consistent: bool = Query(None),
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await DetectionService(db, current_user["customer_id"]).list_source_verifications(is_consistent)


@router.post("/source-verifications", response_model=SourceVerificationResponse, status_code=201)
async def create_source_verification(body: dict,
    current_user: dict = Depends(require_permission("detection", "create")), db: AsyncSession = Depends(get_db)):
    return await DetectionService(db, current_user["customer_id"]).create_source_verification(body)


# ── Sentiment ────────────────────────────────────────────────────

@router.get("/sentiment", response_model=list[SentimentResponse])
async def list_sentiment(sentiment: str = Query(None), is_alert: bool = Query(None),
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await DetectionService(db, current_user["customer_id"]).list_sentiment_results(sentiment, is_alert)


@router.get("/sentiment/summary")
async def get_sentiment_summary(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await DetectionService(db, current_user["customer_id"]).get_sentiment_summary()

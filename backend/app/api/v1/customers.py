"""Customer (tenant) management endpoints — platform admin only."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.core.exceptions import ForbiddenException
from app.core.pagination import PaginationParams, PaginatedResponse
from app.schemas.customer import CustomerCreate, CustomerResponse, CustomerUpdate
from app.services.customer_service import CustomerService

router = APIRouter(tags=["Customers"])


@router.get("/", response_model=PaginatedResponse[CustomerResponse])
async def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all customers (super admin only)."""
    if not current_user["is_super_admin"]:
        raise ForbiddenException()
    svc = CustomerService(db)
    pagination = PaginationParams(page=page, page_size=page_size)
    items, total = await svc.list_customers(pagination, search)
    return PaginatedResponse.create(items, total, pagination)


@router.post("/", response_model=CustomerResponse, status_code=201)
async def create_customer(
    body: CustomerCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new customer tenant."""
    if not current_user["is_super_admin"]:
        raise ForbiddenException()
    svc = CustomerService(db)
    return await svc.create_customer(body.model_dump())


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get customer details."""
    if not current_user["is_super_admin"] and customer_id != current_user["customer_id"]:
        raise ForbiddenException()
    svc = CustomerService(db)
    return await svc.get_customer(customer_id)


@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: uuid.UUID,
    body: CustomerUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update customer settings."""
    if not current_user["is_super_admin"]:
        raise ForbiddenException()
    svc = CustomerService(db)
    return await svc.update_customer(customer_id, body.model_dump(exclude_unset=True))


@router.delete("/{customer_id}")
async def delete_customer(
    customer_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a customer. Super admin only, irreversible."""
    if not current_user["is_super_admin"]:
        raise ForbiddenException()
    from sqlalchemy import delete
    from app.models.customer import Customer
    await db.execute(delete(Customer).where(Customer.id == customer_id))
    await db.commit()
    return {"deleted": True}

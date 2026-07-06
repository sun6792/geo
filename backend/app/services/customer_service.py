"""Customer (tenant) lifecycle management service."""

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.core.pagination import PaginationParams
from app.models.customer import Customer


class CustomerService:
    """Platform-level customer management (super admin only)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_customers(self, pagination: PaginationParams, search: Optional[str] = None) -> tuple[list[Customer], int]:
        query = select(Customer)
        count_q = select(func.count(Customer.id))

        if search:
            filter_clause = Customer.name.ilike(f"%{search}%") | Customer.company_name.ilike(f"%{search}%")
            query = query.where(filter_clause)
            count_q = count_q.where(filter_clause)

        total = (await self.db.execute(count_q)).scalar() or 0
        customers = (await self.db.execute(query.offset(pagination.offset).limit(pagination.limit).order_by(Customer.created_at.desc()))).scalars().all()
        return list(customers), total

    async def create_customer(self, data: dict) -> Customer:
        existing = (await self.db.execute(select(Customer).where(Customer.slug == data["slug"]))).scalar_one_or_none()
        if existing:
            raise ConflictException(f"Customer with slug '{data['slug']}' already exists")
        customer = Customer(**data)
        self.db.add(customer)
        await self.db.flush()
        return customer

    async def get_customer(self, customer_id: uuid.UUID) -> Customer:
        result = await self.db.execute(select(Customer).where(Customer.id == customer_id))
        customer = result.scalar_one_or_none()
        if not customer:
            raise NotFoundException("Customer", str(customer_id))
        return customer

    async def update_customer(self, customer_id: uuid.UUID, data: dict) -> Customer:
        customer = await self.get_customer(customer_id)
        for key, value in data.items():
            if value is not None and hasattr(customer, key):
                setattr(customer, key, value)
        await self.db.flush()
        return customer

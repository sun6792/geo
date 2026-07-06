"""P3 SaaS Billing Service — Plans, Orders, Payments, Quota Management."""

import uuid
from datetime import datetime, timezone, date, timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.core.pagination import PaginationParams
from app.models.billing import Plan, Order, Payment, UsageRecord, QuotaAlert
from app.models.customer import Customer


class BillingService:
    """SaaS billing orchestration: plans, orders, payments, quota enforcement."""

    def __init__(self, db: AsyncSession, customer_id: uuid.UUID | None = None):
        self.db = db
        self.customer_id = customer_id

    # ── Plans ─────────────────────────────────────────────────

    async def list_plans(self, is_public: bool = True) -> list[Plan]:
        query = select(Plan).order_by(Plan.tier, Plan.sort_order)
        if is_public:
            query = query.where(Plan.is_public == True, Plan.is_active == True)
        return list((await self.db.execute(query)).scalars().all())

    async def create_plan(self, data: dict) -> Plan:
        plan = Plan(**data)
        self.db.add(plan)
        await self.db.flush()
        return plan

    async def update_plan(self, plan_id: uuid.UUID, data: dict) -> Plan:
        result = await self.db.execute(select(Plan).where(Plan.id == plan_id))
        plan = result.scalar_one_or_none()
        if not plan:
            raise NotFoundException("Plan", str(plan_id))
        for k, v in data.items():
            if v is not None and hasattr(plan, k):
                setattr(plan, k, v)
        await self.db.flush()
        return plan

    # ── Orders ────────────────────────────────────────────────

    async def list_orders(self, pagination: PaginationParams,
                           status: Optional[str] = None) -> tuple[list[Order], int]:
        query = select(Order)
        count_q = select(func.count(Order.id))
        if self.customer_id:
            query = query.where(Order.customer_id == self.customer_id)
            count_q = count_q.where(Order.customer_id == self.customer_id)
        if status:
            query = query.where(Order.status == status)
            count_q = count_q.where(Order.status == status)

        total = (await self.db.execute(count_q)).scalar() or 0
        items = (await self.db.execute(
            query.order_by(Order.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
        )).scalars().all()
        return list(items), total

    async def create_order(self, data: dict) -> Order:
        """Create a new order for subscription/renewal/upgrade."""
        if not self.customer_id:
            raise ValidationException("customer_id is required to create an order")

        # Validate plan exists
        plan = (await self.db.execute(select(Plan).where(Plan.id == data["plan_id"], Plan.is_active == True))).scalar_one_or_none()
        if not plan:
            raise NotFoundException("Plan", str(data["plan_id"]))

        # Calculate dates
        today = date.today()
        billing_cycle = data.get("billing_cycle", "monthly")
        start_date = data.get("start_date", today)
        if billing_cycle == "monthly":
            end_date = start_date + timedelta(days=30)
        elif billing_cycle == "yearly":
            end_date = start_date + timedelta(days=365)
        else:
            end_date = start_date + timedelta(days=30)

        # Calculate amount using Decimal for financial precision
        from decimal import Decimal
        price = plan.yearly_price if billing_cycle == "yearly" else plan.monthly_price
        amount = Decimal(str(price))  # Convert Numeric→Decimal safely
        if data.get("order_type") == "upgrade":
            # Prorated upgrade amount with Decimal precision
            remaining = await self._get_remaining_value()
            amount = max(amount - remaining, Decimal("0"))

        order = Order(
            customer_id=self.customer_id,
            plan_id=data["plan_id"],
            order_type=data.get("order_type", "new"),
            billing_cycle=billing_cycle,
            amount=amount,
            status="pending",
            start_date=start_date,
            end_date=end_date,
            payment_method=data.get("payment_method", "manual"),
            notes=data.get("notes"),
            created_by=data.get("created_by"),
        )
        self.db.add(order)
        await self.db.flush()

        # Create payment record
        self.db.add(Payment(
            customer_id=self.customer_id,
            order_id=order.id,
            amount=amount,
            payment_method=data.get("payment_method", "manual"),
            status="pending",
        ))
        await self.db.flush()
        return order

    async def confirm_payment(self, order_id: uuid.UUID, transaction_id: Optional[str] = None) -> Order:
        """Confirm payment and activate the order with cross-tenant validation."""
        # Cross-tenant safety: if customer_id is set, verify order ownership
        query = select(Order).where(Order.id == order_id)
        if self.customer_id:
            query = query.where(Order.customer_id == self.customer_id)
        result = await self.db.execute(query)
        order = result.scalar_one_or_none()
        if not order:
            raise NotFoundException("Order", str(order_id))

        order.status = "paid"
        order.payment_ref = transaction_id

        # Activate subscription on customer
        if self.customer_id:
            customer = (await self.db.execute(select(Customer).where(Customer.id == order.customer_id))).scalar_one_or_none()
            if customer:
                plan = (await self.db.execute(select(Plan).where(Plan.id == order.plan_id))).scalar_one_or_none()
                if plan:
                    customer.subscription_tier = plan.code
                    customer.max_users = plan.quotas.get("max_users", 5)
                    customer.max_kb_assets = plan.quotas.get("max_kb_assets", 500)
                    customer.max_content_per_month = plan.quotas.get("max_content_month", 50)
                    customer.status = "active"

        # Update payment record
        payment_result = await self.db.execute(
            select(Payment).where(Payment.order_id == order_id).order_by(Payment.created_at.desc()).limit(1)
        )
        payment = payment_result.scalar_one_or_none()
        if payment:
            payment.status = "success"
            payment.transaction_id = transaction_id
            payment.paid_at = datetime.now(timezone.utc)

        order.status = "active"
        await self.db.flush()
        return order

    async def _get_remaining_value(self):
        """Calculate remaining value of current subscription for upgrade proration (Decimal precision)."""
        from decimal import Decimal
        if not self.customer_id:
            return Decimal("0")
        result = await self.db.execute(
            select(Order).where(
                Order.customer_id == self.customer_id,
                Order.status == "active",
            ).order_by(Order.created_at.desc()).limit(1)
        )
        active = result.scalar_one_or_none()
        if not active or not active.end_date:
            return Decimal("0")
        remaining_days = (active.end_date - date.today()).days
        if remaining_days <= 0:
            return Decimal("0")
        total_days = (active.end_date - active.start_date).days or 30
        # Use Decimal arithmetic for financial precision
        amount = Decimal(str(active.amount))
        ratio = Decimal(str(remaining_days)) / Decimal(str(total_days))
        return amount * ratio

    # ── Quota Management ──────────────────────────────────────

    async def check_quota(self, usage_type: str) -> dict:
        """Check if the current customer has remaining quota for a usage type."""
        if not self.customer_id:
            return {"allowed": True, "remaining": -1, "limit": -1}

        # Get plan quotas
        active_order = (await self.db.execute(
            select(Order).where(Order.customer_id == self.customer_id, Order.status == "active").order_by(Order.created_at.desc()).limit(1)
        )).scalar_one_or_none()

        # Map usage_type to plan quota keys (must match seed data keys)
        QUOTA_KEY_MAP = {
            "llm_call": "max_llm_calls_month",
            "publish": "max_content_month",
            "detection": "max_detection_tasks",
            "user": "max_users",
            "storage": "max_kb_assets",
            "channel": "max_channels",
        }

        if not active_order:
            # Free tier defaults
            defaults = {"llm_call": 100, "publish": 20, "detection": 10, "user": 5, "storage": 500}
            limit = defaults.get(usage_type, 50)
        else:
            plan = (await self.db.execute(select(Plan).where(Plan.id == active_order.plan_id))).scalar_one_or_none()
            quota_key = QUOTA_KEY_MAP.get(usage_type, f"max_{usage_type}_month")
            limit = plan.quotas.get(quota_key, 50) if plan else 50

        # Count current usage this month
        month_start = date.today().replace(day=1)
        result = await self.db.execute(
            select(func.sum(UsageRecord.usage_count)).where(
                UsageRecord.customer_id == self.customer_id,
                UsageRecord.usage_type == usage_type,
                UsageRecord.usage_date >= month_start,
            )
        )
        used = result.scalar() or 0
        remaining = max(0, limit - used)

        # Trigger alert if threshold exceeded
        if limit > 0 and used / limit >= 0.8:
            existing_alert = (await self.db.execute(
                select(QuotaAlert).where(
                    QuotaAlert.customer_id == self.customer_id,
                    QuotaAlert.usage_type == usage_type,
                    QuotaAlert.is_triggered == True,
                    QuotaAlert.acknowledged == False,
                )
            )).scalar_one_or_none()
            if not existing_alert:
                self.db.add(QuotaAlert(customer_id=self.customer_id, usage_type=usage_type, threshold_pct=80, is_triggered=True, triggered_at=datetime.now(timezone.utc)))

        return {"allowed": remaining > 0, "remaining": remaining, "limit": limit, "used": used}

    async def record_usage(self, usage_type: str, count: int = 1) -> UsageRecord:
        """Record a usage event for quota tracking."""
        if not self.customer_id:
            raise ValidationException("customer_id required")

        check = await self.check_quota(usage_type)
        if not check["allowed"]:
            raise ValidationException(f"Quota exceeded for {usage_type}. Limit: {check['limit']}, Used: {check['used']}")

        record = UsageRecord(
            customer_id=self.customer_id, usage_type=usage_type,
            usage_count=count, quota_limit=check["limit"],
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def get_usage_stats(self) -> dict:
        """Get monthly usage statistics for the current customer."""
        if not self.customer_id:
            return {}
        month_start = date.today().replace(day=1)
        result = await self.db.execute(
            select(UsageRecord.usage_type, func.sum(UsageRecord.usage_count)).where(
                UsageRecord.customer_id == self.customer_id,
                UsageRecord.usage_date >= month_start,
            ).group_by(UsageRecord.usage_type)
        )
        stats = {}
        for usage_type, total in result.all():
            check = await self.check_quota(usage_type)
            stats[usage_type] = {"used": int(total or 0), "limit": check["limit"], "remaining": check["remaining"]}
        return stats

    async def get_alerts(self) -> list[QuotaAlert]:
        if not self.customer_id:
            return []
        result = await self.db.execute(
            select(QuotaAlert).where(QuotaAlert.customer_id == self.customer_id, QuotaAlert.acknowledged == False).order_by(QuotaAlert.triggered_at.desc())
        )
        return list(result.scalars().all())

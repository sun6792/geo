"""Account service: user, role, and permission management."""

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.core.pagination import PaginationParams
from app.core.security import hash_password
from app.models.account import Permission, Role, RolePermission, User, UserRole


class AccountService:
    """User and role management within a customer tenant."""

    def __init__(self, db: AsyncSession, customer_id: uuid.UUID):
        self.db = db
        self.customer_id = customer_id

    # ── Users ─────────────────────────────────────────────────

    async def list_users(self, pagination: PaginationParams, search: Optional[str] = None) -> tuple[list[User], int]:
        query = select(User).where(User.customer_id == self.customer_id)
        count_q = select(func.count(User.id)).where(User.customer_id == self.customer_id)

        if search:
            filter_clause = User.email.ilike(f"%{search}%") | User.display_name.ilike(f"%{search}%")
            query = query.where(filter_clause)
            count_q = count_q.where(filter_clause)

        total = (await self.db.execute(count_q)).scalar() or 0
        users = (await self.db.execute(query.offset(pagination.offset).limit(pagination.limit).order_by(User.created_at.desc()))).scalars().all()
        return list(users), total

    async def create_user(self, email: str, password: str, display_name: str, phone: Optional[str], role_ids: list[uuid.UUID], username: str = "") -> User:
        existing = (await self.db.execute(select(User).where(User.customer_id == self.customer_id, User.email == email))).scalar_one_or_none()
        if existing:
            raise ConflictException(f"该邮箱已存在")
        if username:
            existing_u = (await self.db.execute(select(User).where(User.username == username))).scalar_one_or_none()
            if existing_u:
                raise ConflictException(f"用户名 '{username}' 已被使用")

        user = User(
            customer_id=self.customer_id,
            username=username or None,
            email=email,
            password_hash=hash_password(password),
            display_name=display_name,
            phone=phone,
        )
        self.db.add(user)
        await self.db.flush()

        # Assign roles
        for rid in role_ids:
            role = (await self.db.execute(select(Role).where(Role.id == rid))).scalar_one_or_none()
            if role and (role.customer_id == self.customer_id or role.customer_id is None):
                self.db.add(UserRole(user_id=user.id, role_id=rid))

        await self.db.flush()
        return user

    async def update_user(self, user_id: uuid.UUID, **kwargs) -> User:
        user = await self._get_user(user_id)
        for key, value in kwargs.items():
            if value is not None and hasattr(user, key):
                setattr(user, key, value)
        await self.db.flush()
        return user

    async def deactivate_user(self, user_id: uuid.UUID) -> User:
        user = await self._get_user(user_id)
        user.is_active = False
        await self.db.flush()
        return user

    async def assign_roles(self, user_id: uuid.UUID, role_ids: list[uuid.UUID]) -> User:
        await self._get_user(user_id)
        # Remove existing roles
        existing = (await self.db.execute(select(UserRole).where(UserRole.user_id == user_id))).scalars().all()
        for ur in existing:
            await self.db.delete(ur)
        # Add new roles
        for rid in role_ids:
            role = (await self.db.execute(select(Role).where(Role.id == rid))).scalar_one_or_none()
            if role:
                self.db.add(UserRole(user_id=user_id, role_id=rid, granted_by=user_id))
        await self.db.flush()
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one()

    async def _get_user(self, user_id: uuid.UUID) -> User:
        result = await self.db.execute(
            select(User).where(User.id == user_id, User.customer_id == self.customer_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundException("User", str(user_id))
        return user

    async def get_user(self, user_id: uuid.UUID) -> User:
        return await self._get_user(user_id)

    # ── Roles ─────────────────────────────────────────────────

    async def list_roles(self) -> list[Role]:
        result = await self.db.execute(
            select(Role).where(
                (Role.customer_id == self.customer_id) | (Role.customer_id.is_(None))
            ).order_by(Role.created_at)
        )
        return list(result.scalars().all())

    async def create_role(self, name: str, code: str, description: Optional[str], permission_ids: list[uuid.UUID]) -> Role:
        existing = (await self.db.execute(
            select(Role).where(Role.customer_id == self.customer_id, Role.code == code)
        )).scalar_one_or_none()
        if existing:
            raise ConflictException(f"Role with code '{code}' already exists")

        role = Role(customer_id=self.customer_id, name=name, code=code, description=description)
        self.db.add(role)
        await self.db.flush()

        for pid in permission_ids:
            perm = (await self.db.execute(select(Permission).where(Permission.id == pid))).scalar_one_or_none()
            if perm:
                self.db.add(RolePermission(role_id=role.id, permission_id=pid))

        await self.db.flush()
        return role

    async def update_role(self, role_id: uuid.UUID, **kwargs) -> Role:
        role = await self._get_role(role_id)
        if role.is_system:
            raise ConflictException("System roles cannot be modified")

        permission_ids = kwargs.pop("permission_ids", None)

        for key, value in kwargs.items():
            if value is not None and hasattr(role, key):
                setattr(role, key, value)

        if permission_ids is not None:
            # Replace all permissions
            existing = (await self.db.execute(select(RolePermission).where(RolePermission.role_id == role_id))).scalars().all()
            for rp in existing:
                await self.db.delete(rp)
            for pid in permission_ids:
                self.db.add(RolePermission(role_id=role_id, permission_id=pid))

        await self.db.flush()
        return role

    async def delete_role(self, role_id: uuid.UUID) -> None:
        role = await self._get_role(role_id)
        if role.is_system:
            raise ConflictException("System roles cannot be deleted")
        await self.db.delete(role)
        await self.db.flush()

    async def set_role_permissions(self, role_id: uuid.UUID, permission_ids: list[uuid.UUID]) -> Role:
        role = await self._get_role(role_id)
        # Clear existing
        existing = (await self.db.execute(select(RolePermission).where(RolePermission.role_id == role_id))).scalars().all()
        for rp in existing:
            await self.db.delete(rp)
        # Set new
        for pid in permission_ids:
            self.db.add(RolePermission(role_id=role_id, permission_id=pid))
        await self.db.flush()
        return role

    async def _get_role(self, role_id: uuid.UUID) -> Role:
        result = await self.db.execute(
            select(Role).where(Role.id == role_id, (Role.customer_id == self.customer_id) | (Role.customer_id.is_(None)))
        )
        role = result.scalar_one_or_none()
        if not role:
            raise NotFoundException("Role", str(role_id))
        return role

    # ── Permissions ───────────────────────────────────────────

    async def list_permissions(self) -> list[Permission]:
        result = await self.db.execute(select(Permission).order_by(Permission.resource, Permission.action))
        return list(result.scalars().all())

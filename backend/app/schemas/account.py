"""Pydantic schemas for authentication and account management."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ── Auth ──────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    email: str = Field(..., max_length=320)
    password: str = Field(..., min_length=6, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=128)


# ── User ──────────────────────────────────────────────────────────


class UserCreate(BaseModel):
    email: str = Field(..., max_length=320)
    password: str = Field(..., min_length=6, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = None
    role_ids: list[uuid.UUID] = Field(default_factory=list)


class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    is_super_admin: bool = False
    is_active: bool = True
    last_login_at: Optional[datetime] = None
    created_at: datetime
    roles: list = Field(default_factory=list)

    model_config = {"from_attributes": True}


class UserBrief(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    is_active: bool

    model_config = {"from_attributes": True}


# ── Role ──────────────────────────────────────────────────────────


class RoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    permission_ids: list[uuid.UUID] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    permission_ids: Optional[list[uuid.UUID]] = None


class RoleResponse(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    description: Optional[str] = None
    is_system: bool = False
    created_at: datetime
    permissions: list["PermissionBrief"] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class RoleBrief(BaseModel):
    id: uuid.UUID
    name: str
    code: str

    model_config = {"from_attributes": True}


# ── Permission ────────────────────────────────────────────────────


class PermissionResponse(BaseModel):
    id: uuid.UUID
    code: str
    resource: str
    action: str
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class PermissionBrief(BaseModel):
    id: uuid.UUID
    code: str
    resource: str
    action: str

    model_config = {"from_attributes": True}


# ── User Role Assignment ──────────────────────────────────────────


class AssignRolesRequest(BaseModel):
    role_ids: list[uuid.UUID]

"""Pydantic schemas for customer (tenant) management."""

import uuid
from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=100)
    owner_email: str = Field(..., max_length=320)
    company_name: Optional[str] = Field(None, max_length=300)
    industry: Optional[str] = Field(None, max_length=100)
    subscription_tier: str = "basic"
    plan_id: Optional[uuid.UUID] = Field(None, description="绑定的服务档位ID")
    service_start: Optional[date] = Field(None, description="服务开始日期")
    service_end: Optional[date] = Field(None, description="服务结束日期")
    max_users: int = 5
    max_kb_assets: int = 500
    max_content_per_month: int = 50


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    company_name: Optional[str] = Field(None, max_length=300)
    industry: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = None
    subscription_tier: Optional[str] = None
    plan_id: Optional[uuid.UUID] = Field(None, description="升级/更改服务档位")
    service_start: Optional[date] = Field(None, description="更新服务开始日期")
    service_end: Optional[date] = Field(None, description="更新服务结束日期")
    max_users: Optional[int] = None
    max_kb_assets: Optional[int] = None
    max_content_per_month: Optional[int] = None


class CustomerResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    owner_email: str
    company_name: Optional[str] = None
    industry: Optional[str] = None
    status: str
    subscription_tier: str
    plan_id: Optional[uuid.UUID] = None
    service_start: Optional[date] = None
    service_end: Optional[date] = None
    max_users: int
    max_kb_assets: int
    max_content_per_month: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CustomerBrief(BaseModel):
    id: uuid.UUID
    name: str
    slug: str

    model_config = {"from_attributes": True}


class ApiKeyCreate(BaseModel):
    key_name: str = Field(..., max_length=100)
    scopes: list[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    key_name: str
    key_prefix: str
    scopes: list
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    created_at: datetime
    revoked_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ApiKeyCreatedResponse(ApiKeyResponse):
    """Returned once when a key is created — includes the raw key value."""
    raw_key: str

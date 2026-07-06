"""Pydantic schemas for Knowledge Base."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    name: str = Field(..., max_length=200)
    slug: str = Field(..., max_length=200)
    parent_id: Optional[uuid.UUID] = None
    description: Optional[str] = None
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    sort_order: Optional[int] = None


class CategoryResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    parent_id: Optional[uuid.UUID] = None
    description: Optional[str] = None
    sort_order: int
    children: list["CategoryResponse"] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}


class AssetCreate(BaseModel):
    title: str = Field(..., max_length=500)
    slug: str = Field(..., max_length=500)
    asset_type: str = Field(..., pattern=r"^(basic|marketing|multimodal)$")
    content_type: str = Field(default="text")
    content_text: Optional[str] = None
    content_json: Optional[dict] = None
    category_id: Optional[uuid.UUID] = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class AssetUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    content_type: Optional[str] = None
    content_text: Optional[str] = None
    content_json: Optional[dict] = None
    category_id: Optional[uuid.UUID] = None
    status: Optional[str] = None
    tags: Optional[list[str]] = None
    metadata: Optional[dict] = None


class AssetResponse(BaseModel):
    id: uuid.UUID
    title: str
    slug: str
    asset_type: str
    content_type: str
    content_text: Optional[str] = None
    content_json: Optional[dict] = None
    category_id: Optional[uuid.UUID] = None
    status: str
    version: int
    is_latest: bool
    tags: list = Field(default_factory=list)
    extra_meta: dict = Field(default_factory=dict)
    file_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssetVersionResponse(BaseModel):
    id: uuid.UUID
    version: int
    is_latest: bool
    status: str
    created_at: datetime
    updated_by: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}

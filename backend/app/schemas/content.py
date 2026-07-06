"""Pydantic schemas for Content Creation."""

import uuid
from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, Field


class ContentBriefCreate(BaseModel):
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    content_type: str = Field(default="blog_post")
    target_audience: Optional[str] = None
    target_keywords: list[str] = Field(default_factory=list)
    tone_style: Optional[str] = None
    word_count_target: Optional[int] = None
    source_kb_asset_ids: list[uuid.UUID] = Field(..., min_length=1)  # HARD CONSTRAINT
    priority: int = 0
    due_date: Optional[date] = None


class ContentBriefUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    content_type: Optional[str] = None
    target_audience: Optional[str] = None
    target_keywords: Optional[list[str]] = None
    tone_style: Optional[str] = None
    word_count_target: Optional[int] = None
    priority: Optional[int] = None
    status: Optional[str] = None


class ContentBriefResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    content_type: str
    target_keywords: list
    tone_style: Optional[str] = None
    source_kb_asset_ids: list[uuid.UUID]
    status: str
    priority: int
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContentDraftResponse(BaseModel):
    id: uuid.UUID
    brief_id: uuid.UUID
    version: int
    title: str
    body_markdown: str
    seo_metadata: dict
    word_count: Optional[int] = None
    kb_sources: list
    status: str
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContentTemplateCreate(BaseModel):
    name: str = Field(..., max_length=200)
    content_type: str
    prompt_template: str
    system_prompt: Optional[str] = None
    variables: list = Field(default_factory=list)


class ContentTemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    content_type: str
    prompt_template: str
    system_prompt: Optional[str] = None
    variables: list
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class GenerateRequest(BaseModel):
    """Request to trigger AI content generation for a brief."""
    model_provider: Optional[str] = None  # defaults to system config
    model_name: Optional[str] = None

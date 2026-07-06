"""Pydantic schemas for Review Workflow."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SubmitReviewRequest(BaseModel):
    """Submit a draft for internal review."""
    pass


class AdvanceToClientRequest(BaseModel):
    """Advance to client review after internal approval."""
    client_email: str = Field(..., max_length=320)
    client_name: str = Field(..., max_length=200)


class ReviewActionRequest(BaseModel):
    """Approve, reject, or request changes."""
    comment: Optional[str] = None


class ReviewCommentCreate(BaseModel):
    comment_text: str
    comment_type: str = "general"
    parent_id: Optional[uuid.UUID] = None
    selection_start: Optional[int] = None
    selection_end: Optional[int] = None
    selected_text: Optional[str] = None


class ReviewCommentResponse(BaseModel):
    id: uuid.UUID
    review_record_id: uuid.UUID
    parent_id: Optional[uuid.UUID] = None
    comment_text: str
    comment_type: str
    selection_start: Optional[int] = None
    selection_end: Optional[int] = None
    selected_text: Optional[str] = None
    is_resolved: bool
    created_by: uuid.UUID
    created_at: datetime
    replies: list["ReviewCommentResponse"] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ReviewRecordResponse(BaseModel):
    id: uuid.UUID
    draft_id: uuid.UUID
    stage: str
    status: str
    reviewer_id: Optional[uuid.UUID] = None
    client_reviewer_email: Optional[str] = None
    client_reviewer_name: Optional[str] = None
    client_access_token: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    comments: list[ReviewCommentResponse] = Field(default_factory=list)
    approval_chain: list["ApprovalChainResponse"] = Field(default_factory=list)
    checklist_results: list["ChecklistResultResponse"] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ApprovalChainResponse(BaseModel):
    id: uuid.UUID
    action: str
    actor_type: str
    actor_id: Optional[uuid.UUID] = None
    actor_email: Optional[str] = None
    comment: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChecklistItemResponse(BaseModel):
    id: uuid.UUID
    stage: str
    item_text: str
    sort_order: int

    model_config = {"from_attributes": True}


class ChecklistResultResponse(BaseModel):
    id: uuid.UUID
    checklist_id: uuid.UUID
    is_checked: bool
    checked_by: Optional[uuid.UUID] = None
    checked_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

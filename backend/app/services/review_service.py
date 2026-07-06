"""Review workflow service — dual-review state machine with hard gate enforcement.

Core business rule: Content MUST pass internal_review before client_review.
Both reviews MUST be approved before publishing. This cannot be bypassed.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ReviewGateException, ValidationException
from app.core.security import generate_client_access_token
from app.models.content import ContentDraft
from app.models.review import (
    ReviewRecord, ReviewComment, ReviewApprovalChain,
    ReviewChecklist, ReviewChecklistResult,
)


class ReviewService:
    """Dual-review orchestration with hard gate enforcement."""

    def __init__(self, db: AsyncSession, customer_id: uuid.UUID):
        self.db = db
        self.customer_id = customer_id

    # ── Submit for Review ─────────────────────────────────────

    async def submit_for_internal_review(self, draft_id: uuid.UUID, submitted_by: uuid.UUID) -> ReviewRecord:
        """Submit a draft for internal review. Creates the internal_review record."""
        draft = await self._get_draft(draft_id)

        # Validate: draft must be in correct state
        if draft.status not in ("draft", "revisions_requested"):
            raise ValidationException(f"Cannot submit draft in '{draft.status}' status for review")

        # Create internal review record
        record = ReviewRecord(
            customer_id=self.customer_id,
            draft_id=draft_id,
            stage="internal_review",
            status="pending",
        )
        self.db.add(record)

        # Update draft status
        draft.status = "in_review"

        # Create default checklist results
        checklists = (await self.db.execute(
            select(ReviewChecklist).where(
                ReviewChecklist.customer_id == self.customer_id,
                ReviewChecklist.stage == "internal_review",
                ReviewChecklist.is_active == True,
            )
        )).scalars().all()

        for cl in checklists:
            self.db.add(ReviewChecklistResult(
                customer_id=self.customer_id,
                review_record_id=record.id,
                checklist_id=cl.id,
            ))

        # Record approval chain
        self.db.add(ReviewApprovalChain(
            customer_id=self.customer_id,
            review_record_id=record.id,
            action="submitted",
            actor_type="internal_user",
            actor_id=submitted_by,
        ))

        await self.db.flush()
        return record

    async def advance_to_client_review(self, draft_id: uuid.UUID, reviewer_id: uuid.UUID,
                                        client_email: str, client_name: str) -> ReviewRecord:
        """Advance to client review stage. HARD GATE: internal_review must be approved first."""

        # Check: internal review must exist and be approved
        internal = (await self.db.execute(
            select(ReviewRecord).where(
                ReviewRecord.draft_id == draft_id,
                ReviewRecord.stage == "internal_review",
            )
        )).scalar_one_or_none()

        if not internal:
            raise ReviewGateException("internal_review", str(draft_id))

        if internal.status != "approved":
            raise ReviewGateException("internal_review", str(draft_id))

        # Check: client review must not already exist
        existing = (await self.db.execute(
            select(ReviewRecord).where(
                ReviewRecord.draft_id == draft_id,
                ReviewRecord.stage == "client_review",
            )
        )).scalar_one_or_none()

        if existing:
            raise ValidationException("Client review already exists for this draft")

        # Generate client access token
        token = generate_client_access_token()

        # Create client review record
        record = ReviewRecord(
            customer_id=self.customer_id,
            draft_id=draft_id,
            stage="client_review",
            status="pending",
            client_reviewer_email=client_email,
            client_reviewer_name=client_name,
            client_access_token=token,
            client_token_expires=datetime.now(timezone.utc) + timedelta(hours=72),
        )
        self.db.add(record)

        # Create client review checklists
        checklists = (await self.db.execute(
            select(ReviewChecklist).where(
                ReviewChecklist.customer_id == self.customer_id,
                ReviewChecklist.stage == "client_review",
                ReviewChecklist.is_active == True,
            )
        )).scalars().all()

        for cl in checklists:
            self.db.add(ReviewChecklistResult(
                customer_id=self.customer_id,
                review_record_id=record.id,
                checklist_id=cl.id,
            ))

        await self.db.flush()
        return record

    # ── Review Actions ────────────────────────────────────────

    async def approve(self, review_id: uuid.UUID, actor_id: uuid.UUID,
                       actor_type: str = "internal_user", comment: Optional[str] = None) -> ReviewRecord:
        """Approve a review stage."""
        record = await self._get_review(review_id)

        if record.status != "pending":
            raise ValidationException(f"Review is already {record.status}")

        record.status = "approved"
        record.reviewer_id = actor_id if actor_type == "internal_user" else record.reviewer_id
        record.reviewed_at = datetime.now(timezone.utc)

        self.db.add(ReviewApprovalChain(
            customer_id=self.customer_id,
            review_record_id=review_id,
            action="approved",
            actor_type=actor_type,
            actor_id=actor_id if actor_type == "internal_user" else None,
            actor_email=None,
            comment=comment,
        ))

        # If client review approved, mark draft as approved
        if record.stage == "client_review":
            draft = await self._get_draft(record.draft_id)
            draft.status = "approved"

        await self.db.flush()
        return record

    async def reject(self, review_id: uuid.UUID, actor_id: uuid.UUID,
                      actor_type: str = "internal_user", comment: Optional[str] = None) -> ReviewRecord:
        """Reject a review stage."""
        record = await self._get_review(review_id)

        record.status = "rejected"
        record.reviewed_at = datetime.now(timezone.utc)

        self.db.add(ReviewApprovalChain(
            customer_id=self.customer_id,
            review_record_id=review_id,
            action="rejected",
            actor_type=actor_type,
            actor_id=actor_id if actor_type == "internal_user" else None,
            comment=comment,
        ))

        # Update draft status
        draft = await self._get_draft(record.draft_id)
        draft.status = "rejected"

        await self.db.flush()
        return record

    async def request_changes(self, review_id: uuid.UUID, actor_id: uuid.UUID,
                               actor_type: str = "internal_user", comment: Optional[str] = None) -> ReviewRecord:
        """Request changes on a review stage."""
        record = await self._get_review(review_id)

        record.status = "changes_requested"
        record.reviewed_at = datetime.now(timezone.utc)

        self.db.add(ReviewApprovalChain(
            customer_id=self.customer_id,
            review_record_id=review_id,
            action="changes_requested",
            actor_type=actor_type,
            actor_id=actor_id if actor_type == "internal_user" else None,
            comment=comment,
        ))

        draft = await self._get_draft(record.draft_id)
        draft.status = "revisions_requested"

        await self.db.flush()
        return record

    # ── Comments ──────────────────────────────────────────────

    async def add_comment(self, review_id: uuid.UUID, created_by: uuid.UUID, comment_text: str,
                           comment_type: str = "general", parent_id: Optional[uuid.UUID] = None,
                           selection_start: Optional[int] = None, selection_end: Optional[int] = None,
                           selected_text: Optional[str] = None) -> ReviewComment:
        """Add a comment to a review."""
        comment = ReviewComment(
            customer_id=self.customer_id,
            review_record_id=review_id,
            parent_id=parent_id,
            comment_text=comment_text,
            comment_type=comment_type,
            selection_start=selection_start,
            selection_end=selection_end,
            selected_text=selected_text,
            created_by=created_by,
        )
        self.db.add(comment)
        await self.db.flush()
        return comment

    async def resolve_comment(self, comment_id: uuid.UUID, resolved_by: uuid.UUID) -> ReviewComment:
        """Mark a review comment as resolved."""
        result = await self.db.execute(
            select(ReviewComment).where(ReviewComment.id == comment_id, ReviewComment.customer_id == self.customer_id)
        )
        comment = result.scalar_one_or_none()
        if not comment:
            raise NotFoundException("ReviewComment", str(comment_id))
        comment.is_resolved = True
        comment.resolved_by = resolved_by
        comment.resolved_at = datetime.now(timezone.utc)
        await self.db.flush()
        return comment

    # ── Queries ───────────────────────────────────────────────

    async def list_reviews(self, stage: Optional[str] = None, status: Optional[str] = None) -> list[ReviewRecord]:
        query = select(ReviewRecord).where(ReviewRecord.customer_id == self.customer_id)
        if stage:
            query = query.where(ReviewRecord.stage == stage)
        if status:
            query = query.where(ReviewRecord.status == status)
        result = await self.db.execute(query.order_by(ReviewRecord.created_at.desc()))
        return list(result.scalars().all())

    async def get_review(self, review_id: uuid.UUID) -> ReviewRecord:
        return await self._get_review(review_id)

    async def get_review_by_token(self, token: str) -> ReviewRecord:
        """Public access: get review by client access token."""
        result = await self.db.execute(
            select(ReviewRecord).where(
                ReviewRecord.client_access_token == token,
                ReviewRecord.customer_id == self.customer_id,
                ReviewRecord.stage == "client_review",
                ReviewRecord.client_token_expires > datetime.now(timezone.utc),
            )
        )
        record = result.scalar_one_or_none()
        if not record:
            raise NotFoundException("Review", "token invalid or expired")
        return record

    # ── Checklists ────────────────────────────────────────────

    async def get_checklists(self, stage: str) -> list[ReviewChecklist]:
        result = await self.db.execute(
            select(ReviewChecklist).where(
                ReviewChecklist.customer_id == self.customer_id,
                ReviewChecklist.stage == stage,
                ReviewChecklist.is_active == True,
            ).order_by(ReviewChecklist.sort_order)
        )
        return list(result.scalars().all())

    async def check_item(self, result_id: uuid.UUID, checked_by: uuid.UUID) -> ReviewChecklistResult:
        result = await self.db.execute(
            select(ReviewChecklistResult).where(
                ReviewChecklistResult.id == result_id,
                ReviewChecklistResult.customer_id == self.customer_id,
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundException("ReviewChecklistResult", str(result_id))
        item.is_checked = True
        item.checked_by = checked_by
        item.checked_at = datetime.now(timezone.utc)
        await self.db.flush()
        return item

    # ── Helpers ───────────────────────────────────────────────

    async def _get_review(self, review_id: uuid.UUID) -> ReviewRecord:
        result = await self.db.execute(
            select(ReviewRecord).where(ReviewRecord.id == review_id, ReviewRecord.customer_id == self.customer_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            raise NotFoundException("ReviewRecord", str(review_id))
        return record

    async def _get_draft(self, draft_id: uuid.UUID) -> ContentDraft:
        from app.models.content import ContentDraft
        result = await self.db.execute(
            select(ContentDraft).where(ContentDraft.id == draft_id, ContentDraft.customer_id == self.customer_id)
        )
        draft = result.scalar_one_or_none()
        if not draft:
            raise NotFoundException("ContentDraft", str(draft_id))
        return draft

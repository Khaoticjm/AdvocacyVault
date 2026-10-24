import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.adjuster.models import ClaimReview, EvidenceItem, ReviewStatus
from app.modules.adjuster.schemas import (
    ClaimReviewCreate, ClaimReviewSummaryUpdate, EvidenceItemCreate,
)
from app.modules.verifier.models import VerificationReport, VerdictEnum
from app.security import encrypt_phi, decrypt_phi
from app.modules.audit.services import write_audit_log


async def create_review(db: AsyncSession, data: ClaimReviewCreate, adjuster_id: uuid.UUID) -> ClaimReview:
    review = ClaimReview(complaint_id=data.complaint_id, adjuster_id=adjuster_id, status=ReviewStatus.IN_REVIEW)
    db.add(review)
    await db.flush()
    await write_audit_log(db, action="CREATE_REVIEW", actor_id=adjuster_id, resource_type="review", resource_id=review.id)
    return review


async def get_review(db: AsyncSession, review_id: uuid.UUID, actor_id: uuid.UUID, ip_hashed: str) -> ClaimReview | None:
    result = await db.execute(
        select(ClaimReview).options(selectinload(ClaimReview.evidence_items)).where(ClaimReview.id == review_id)
    )
    review = result.scalar_one_or_none()
    if review:
        await write_audit_log(db, action="VIEW_REVIEW", actor_id=actor_id, resource_type="review", resource_id=review_id, ip_address_hashed=ip_hashed)
    return review


async def list_reviews(db: AsyncSession, adjuster_id: uuid.UUID) -> List[ClaimReview]:
    result = await db.execute(
        select(ClaimReview).where(ClaimReview.adjuster_id == adjuster_id).order_by(ClaimReview.created_at.desc())
    )
    return list(result.scalars().all())


async def update_summary(db: AsyncSession, review: ClaimReview, data: ClaimReviewSummaryUpdate, actor_id: uuid.UUID) -> ClaimReview:
    review.encrypted_summary = encrypt_phi(data.summary)
    review.severity = data.severity
    await db.flush()
    await write_audit_log(db, action="UPDATE_SUMMARY", actor_id=actor_id, resource_type="review", resource_id=review.id)
    return review


async def add_evidence(db: AsyncSession, review: ClaimReview, data: EvidenceItemCreate, actor_id: uuid.UUID) -> EvidenceItem:
    item = EvidenceItem(
        review_id=review.id,
        encrypted_content=encrypt_phi(data.content),
        content_type=data.content_type,
        sort_order=len(review.evidence_items),
    )
    db.add(item)
    await db.flush()
    await write_audit_log(db, action="ADD_EVIDENCE", actor_id=actor_id, resource_type="evidence_item", resource_id=item.id)
    return item


async def confirm_evidence(db: AsyncSession, item: EvidenceItem, actor_id: uuid.UUID) -> EvidenceItem:
    item.adjuster_confirmed = True
    await db.flush()
    await write_audit_log(db, action="CONFIRM_EVIDENCE", actor_id=actor_id, resource_type="evidence_item", resource_id=item.id)
    return item


async def reorder_evidence(db: AsyncSession, review: ClaimReview, ordered_ids: List[uuid.UUID], actor_id: uuid.UUID) -> List[EvidenceItem]:
    id_to_item = {item.id: item for item in review.evidence_items}
    for i, eid in enumerate(ordered_ids):
        if eid in id_to_item:
            id_to_item[eid].sort_order = i
    await db.flush()
    await write_audit_log(db, action="REORDER_EVIDENCE", actor_id=actor_id, resource_type="review", resource_id=review.id)
    return sorted(review.evidence_items, key=lambda x: x.sort_order)


def compute_input_hash(review: ClaimReview) -> str:
    payload = {
        "review_id": str(review.id),
        "evidence": [
            {"id": str(e.id), "content": e.encrypted_content, "confirmed": e.adjuster_confirmed}
            for e in sorted(review.evidence_items, key=lambda x: x.sort_order)
        ],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


async def assert_escalation_ready(db: AsyncSession, review: ClaimReview) -> None:
    """Three-lock escalation gate. Raises ValueError with plain-English reason."""
    # Lock 1: all evidence confirmed
    unconfirmed = [e for e in review.evidence_items if not e.adjuster_confirmed]
    if unconfirmed:
        raise ValueError(
            f"{len(unconfirmed)} evidence item(s) have not been confirmed by a human adjuster. "
            "Confirm each item before escalating."
        )

    # Lock 2: latest verification report must be PASS or OVERRIDDEN
    from sqlalchemy import select as sa_select
    result = await db.execute(
        sa_select(VerificationReport)
        .where(VerificationReport.review_id == review.id)
        .order_by(VerificationReport.created_at.desc())
        .limit(1)
    )
    latest_report = result.scalar_one_or_none()
    if latest_report is None:
        raise ValueError("No verification report found. Run verification before escalating.")
    if latest_report.verdict not in (VerdictEnum.PASS, VerdictEnum.OVERRIDDEN):
        raise ValueError(
            f"Latest verification verdict is {latest_report.verdict.value}. "
            "Resolve verification issues or submit an override before escalating."
        )

    # Lock 3: input hash must match (no mutations after verification)
    current_hash = compute_input_hash(review)
    if current_hash != latest_report.input_hash:
        raise ValueError(
            "Evidence was modified after the last verification run. "
            "Re-run verification to confirm the updated evidence package."
        )


async def update_status(
    db: AsyncSession, review: ClaimReview, new_status: ReviewStatus, actor_id: uuid.UUID
) -> ClaimReview:
    if new_status == ReviewStatus.ESCALATED:
        await assert_escalation_ready(db, review)
    review.status = new_status
    await db.flush()
    await write_audit_log(db, action="UPDATE_STATUS", actor_id=actor_id, resource_type="review", resource_id=review.id, detail=new_status.value)
    return review


def decrypt_review(review: ClaimReview) -> dict:
    return {
        "id": review.id,
        "complaint_id": review.complaint_id,
        "adjuster_id": review.adjuster_id,
        "status": review.status,
        "summary": decrypt_phi(review.encrypted_summary) if review.encrypted_summary else None,
        "severity": review.severity,
        "evidence_items": [
            {
                "id": e.id,
                "content": decrypt_phi(e.encrypted_content),
                "content_type": e.content_type,
                "adjuster_confirmed": e.adjuster_confirmed,
                "sort_order": e.sort_order,
                "created_at": e.created_at,
            }
            for e in sorted(review.evidence_items, key=lambda x: x.sort_order)
        ],
        "created_at": review.created_at,
        "updated_at": review.updated_at,
    }

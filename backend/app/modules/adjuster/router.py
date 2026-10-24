import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.database import get_db
from app.security import hash_ip
from app.modules.adjuster import services
from app.modules.adjuster.models import ClaimReview, EvidenceItem
from app.modules.adjuster.schemas import (
    ClaimReviewCreate, ClaimReviewRead, ClaimReviewStatusUpdate,
    ClaimReviewSummaryUpdate, EscalationPackage, EvidenceItemCreate,
    EvidenceItemRead, EvidenceReorderRequest,
)

router = APIRouter(tags=["adjuster"])

# Placeholder adjuster ID until auth is wired
_DEMO_ADJUSTER = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _ip(request: Request) -> str:
    fwd = request.headers.get("X-Forwarded-For")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")
    return hash_ip(ip)


async def _get_review_or_404(db: AsyncSession, review_id: uuid.UUID) -> ClaimReview:
    result = await db.execute(
        select(ClaimReview).options(selectinload(ClaimReview.evidence_items)).where(ClaimReview.id == review_id)
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@router.post("/reviews/", response_model=dict, status_code=201)
async def create_review(data: ClaimReviewCreate, db: AsyncSession = Depends(get_db)):
    review = await services.create_review(db, data, _DEMO_ADJUSTER)
    return {"id": str(review.id), "status": review.status.value}


@router.get("/reviews/", response_model=list)
async def list_reviews(db: AsyncSession = Depends(get_db)):
    reviews = await services.list_reviews(db, _DEMO_ADJUSTER)
    return [{"id": str(r.id), "complaint_id": str(r.complaint_id), "status": r.status.value, "severity": r.severity, "created_at": r.created_at} for r in reviews]


@router.get("/reviews/{review_id}", response_model=ClaimReviewRead)
async def get_review(review_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    review = await services.get_review(db, review_id, _DEMO_ADJUSTER, _ip(request))
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    d = services.decrypt_review(review)
    return ClaimReviewRead(**d)


@router.patch("/reviews/{review_id}/status", response_model=dict)
async def update_status(review_id: uuid.UUID, data: ClaimReviewStatusUpdate, db: AsyncSession = Depends(get_db)):
    review = await _get_review_or_404(db, review_id)
    try:
        review = await services.update_status(db, review, data.status, _DEMO_ADJUSTER)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"id": str(review.id), "status": review.status.value}


@router.patch("/reviews/{review_id}/summary", response_model=dict)
async def update_summary(review_id: uuid.UUID, data: ClaimReviewSummaryUpdate, db: AsyncSession = Depends(get_db)):
    review = await _get_review_or_404(db, review_id)
    review = await services.update_summary(db, review, data, _DEMO_ADJUSTER)
    return {"id": str(review.id), "severity": review.severity}


@router.get("/reviews/{review_id}/escalation-package", response_model=EscalationPackage)
async def escalation_package(review_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    review = await _get_review_or_404(db, review_id)
    d = services.decrypt_review(review)
    return EscalationPackage(
        review_id=review.id,
        complaint_id=review.complaint_id,
        status=review.status,
        severity=review.severity,
        summary=d["summary"],
        evidence_items=[EvidenceItemRead(**e) for e in d["evidence_items"]],
        generated_at=datetime.now(timezone.utc),
    )


@router.post("/reviews/{review_id}/evidence", response_model=dict, status_code=201)
async def add_evidence(review_id: uuid.UUID, data: EvidenceItemCreate, db: AsyncSession = Depends(get_db)):
    review = await _get_review_or_404(db, review_id)
    item = await services.add_evidence(db, review, data, _DEMO_ADJUSTER)
    return {"id": str(item.id)}


@router.patch("/reviews/{review_id}/evidence/{item_id}/confirm", response_model=dict)
async def confirm_evidence(review_id: uuid.UUID, item_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    review = await _get_review_or_404(db, review_id)
    item = next((e for e in review.evidence_items if e.id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Evidence item not found")
    item = await services.confirm_evidence(db, item, _DEMO_ADJUSTER)
    return {"id": str(item.id), "adjuster_confirmed": item.adjuster_confirmed}


@router.patch("/reviews/{review_id}/evidence/reorder", response_model=list)
async def reorder_evidence(review_id: uuid.UUID, data: EvidenceReorderRequest, db: AsyncSession = Depends(get_db)):
    review = await _get_review_or_404(db, review_id)
    items = await services.reorder_evidence(db, review, data.ordered_ids, _DEMO_ADJUSTER)
    return [{"id": str(i.id), "sort_order": i.sort_order} for i in items]

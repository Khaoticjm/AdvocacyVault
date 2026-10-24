import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.modules.adjuster.models import ClaimReview
from app.modules.verifier import services
from app.modules.verifier.models import VerificationReport
from app.modules.verifier.schemas import OverrideRequest, VerificationReportPublic, VerificationReportRead
from app.security import decrypt_phi

router = APIRouter(tags=["verifier"])

_DEMO_ADJUSTER = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def _get_review_or_404(db: AsyncSession, review_id: uuid.UUID) -> ClaimReview:
    result = await db.execute(
        select(ClaimReview).options(selectinload(ClaimReview.evidence_items)).where(ClaimReview.id == review_id)
    )
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Review not found")
    return r


async def _get_report_or_404(db: AsyncSession, report_id: uuid.UUID) -> VerificationReport:
    r = await db.get(VerificationReport, report_id)
    if not r:
        raise HTTPException(status_code=404, detail="Verification report not found")
    return r


@router.post("/reviews/{review_id}/verify", response_model=VerificationReportRead, status_code=201)
async def run_verification(review_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    review = await _get_review_or_404(db, review_id)
    report = await services.run_verification(db, review, _DEMO_ADJUSTER)
    import json
    analysis = decrypt_phi(report.encrypted_analysis)
    return VerificationReportRead(
        id=report.id,
        review_id=report.review_id,
        verdict=report.verdict,
        analysis=analysis,
        input_hash=report.input_hash,
        llm_provider=report.llm_provider,
        llm_model_version=report.llm_model_version,
        discrepancy_count=report.discrepancy_count,
        created_at=report.created_at,
    )


@router.get("/reviews/{review_id}/verify", response_model=VerificationReportRead)
async def get_latest_verification(review_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    report = await services.get_latest_report(db, review_id)
    if not report:
        raise HTTPException(status_code=404, detail="No verification report found for this review")
    analysis = decrypt_phi(report.encrypted_analysis)
    return VerificationReportRead(
        id=report.id,
        review_id=report.review_id,
        verdict=report.verdict,
        analysis=analysis,
        input_hash=report.input_hash,
        llm_provider=report.llm_provider,
        llm_model_version=report.llm_model_version,
        discrepancy_count=report.discrepancy_count,
        created_at=report.created_at,
    )


@router.get("/reviews/{review_id}/verifications", response_model=list[VerificationReportPublic])
async def list_verifications(review_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await services.list_reports(db, review_id)


@router.post("/verifications/{report_id}/override", response_model=VerificationReportRead)
async def override_verification(report_id: uuid.UUID, data: OverrideRequest, db: AsyncSession = Depends(get_db)):
    report = await _get_report_or_404(db, report_id)
    try:
        report = await services.create_override(db, report, data.justification, _DEMO_ADJUSTER)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    analysis = decrypt_phi(report.encrypted_analysis)
    return VerificationReportRead(
        id=report.id,
        review_id=report.review_id,
        verdict=report.verdict,
        analysis=analysis,
        input_hash=report.input_hash,
        llm_provider=report.llm_provider,
        llm_model_version=report.llm_model_version,
        discrepancy_count=report.discrepancy_count,
        created_at=report.created_at,
    )

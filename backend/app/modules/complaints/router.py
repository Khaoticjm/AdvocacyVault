import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.security import hash_ip
from app.modules.complaints.schemas import ComplaintCreate, ComplaintPublic, ComplaintRead, ComplaintStatusPublic
from app.modules.complaints import services
from app.modules.anonymizer.utils import scrub_exif

router = APIRouter(tags=["complaints"])


def get_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    return hash_ip(ip)


@router.post("/complaints/", response_model=dict, status_code=201)
async def submit_complaint(
    data: ComplaintCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    complaint = await services.create_complaint(db, data, get_ip(request))
    return {
        "id": str(complaint.id),
        "status": complaint.status.value,
        "human_review_pending": True,
        "message": "Your complaint has been received and will be reviewed by a human advocate.",
    }


@router.get("/complaints/", response_model=List[ComplaintPublic])
async def list_complaints(db: AsyncSession = Depends(get_db)):
    return await services.list_complaints(db)


@router.get("/complaints/{complaint_id}/review-status", response_model=ComplaintStatusPublic)
async def complaint_review_status(complaint_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    complaint = await services.get_complaint(db, complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint


@router.get("/complaints/{complaint_id}", response_model=ComplaintRead)
async def get_complaint(
    complaint_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    # TODO: add adjuster auth dependency
):
    actor_id = uuid.uuid4()  # placeholder until auth wired
    result = await services.get_complaint_decrypted(db, complaint_id, actor_id, get_ip(request))
    if result is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    complaint, narrative = result
    return ComplaintRead(
        id=complaint.id,
        narrative=narrative,
        facility_name=complaint.facility_name,
        incident_date=complaint.incident_date,
        status=complaint.status,
        has_attachments=complaint.has_attachments,
        created_at=complaint.created_at,
    )

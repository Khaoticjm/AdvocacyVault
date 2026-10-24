import uuid
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.complaints.models import Complaint
from app.modules.complaints.schemas import ComplaintCreate
from app.security import encrypt_phi, decrypt_phi
from app.modules.audit.services import write_audit_log


async def create_complaint(
    db: AsyncSession,
    data: ComplaintCreate,
    ip_hashed: str,
) -> Complaint:
    complaint = Complaint(
        encrypted_narrative=encrypt_phi(data.narrative),
        facility_name=data.facility_name,
        incident_date=data.incident_date,
    )
    db.add(complaint)
    await db.flush()
    await write_audit_log(
        db,
        action="CREATE_COMPLAINT",
        resource_type="complaint",
        resource_id=complaint.id,
        ip_address_hashed=ip_hashed,
    )
    return complaint


async def list_complaints(db: AsyncSession) -> List[Complaint]:
    result = await db.execute(select(Complaint).order_by(Complaint.created_at.desc()))
    return list(result.scalars().all())


async def get_complaint(db: AsyncSession, complaint_id: uuid.UUID) -> Complaint | None:
    return await db.get(Complaint, complaint_id)


async def get_complaint_decrypted(
    db: AsyncSession,
    complaint_id: uuid.UUID,
    actor_id: uuid.UUID,
    ip_hashed: str,
) -> tuple[Complaint, str] | None:
    complaint = await db.get(Complaint, complaint_id)
    if complaint is None:
        return None
    narrative = decrypt_phi(complaint.encrypted_narrative)
    await write_audit_log(
        db,
        action="VIEW_COMPLAINT_PHI",
        actor_id=actor_id,
        resource_type="complaint",
        resource_id=complaint_id,
        ip_address_hashed=ip_hashed,
    )
    return complaint, narrative

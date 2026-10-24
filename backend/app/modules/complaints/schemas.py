import uuid
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.modules.complaints.models import ComplaintStatus


class ComplaintCreate(BaseModel):
    narrative: str = Field(..., min_length=20, max_length=8000)
    facility_name: str = Field(..., min_length=2, max_length=255)
    incident_date: Optional[date] = None


class ComplaintRead(BaseModel):
    id: uuid.UUID
    narrative: str  # decrypted — adjuster only
    facility_name: str
    incident_date: Optional[date]
    status: ComplaintStatus
    has_attachments: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ComplaintPublic(BaseModel):
    """No PHI — safe for public dashboard."""
    id: uuid.UUID
    facility_name: str
    incident_date: Optional[date]
    status: ComplaintStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class ComplaintStatusPublic(BaseModel):
    id: uuid.UUID
    status: ComplaintStatus

    model_config = {"from_attributes": True}

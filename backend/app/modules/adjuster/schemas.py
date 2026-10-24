import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from app.modules.adjuster.models import ReviewStatus


class EvidenceItemCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    content_type: str = Field(..., min_length=1, max_length=64)


class EvidenceItemRead(BaseModel):
    id: uuid.UUID
    content: str  # decrypted
    content_type: str
    adjuster_confirmed: bool
    sort_order: int
    created_at: datetime
    model_config = {"from_attributes": True}


class EvidenceReorderRequest(BaseModel):
    ordered_ids: List[uuid.UUID]


class ClaimReviewCreate(BaseModel):
    complaint_id: uuid.UUID


class ClaimReviewSummaryUpdate(BaseModel):
    summary: str = Field(..., min_length=1, max_length=20000)
    severity: int = Field(..., ge=1, le=5)


class ClaimReviewStatusUpdate(BaseModel):
    status: ReviewStatus


class ClaimReviewRead(BaseModel):
    id: uuid.UUID
    complaint_id: uuid.UUID
    adjuster_id: uuid.UUID
    status: ReviewStatus
    summary: Optional[str] = None  # decrypted
    severity: Optional[int] = None
    evidence_items: List[EvidenceItemRead] = []
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class EscalationPackage(BaseModel):
    review_id: uuid.UUID
    complaint_id: uuid.UUID
    status: ReviewStatus
    severity: Optional[int]
    summary: Optional[str]
    evidence_items: List[EvidenceItemRead]
    generated_at: datetime

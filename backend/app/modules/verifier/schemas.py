import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from app.modules.verifier.models import VerdictEnum


class VerificationReportRead(BaseModel):
    id: uuid.UUID
    review_id: uuid.UUID
    verdict: VerdictEnum
    analysis: str  # decrypted
    input_hash: str
    llm_provider: str
    llm_model_version: str
    discrepancy_count: int
    created_at: datetime
    model_config = {"from_attributes": True}


class VerificationReportPublic(BaseModel):
    """No PHI analysis — safe for public history endpoint."""
    id: uuid.UUID
    review_id: uuid.UUID
    verdict: VerdictEnum
    llm_provider: str
    llm_model_version: str
    discrepancy_count: int
    created_at: datetime
    model_config = {"from_attributes": True}


class OverrideRequest(BaseModel):
    justification: str = Field(..., min_length=20, max_length=4000)

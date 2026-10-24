import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class VerdictEnum(str, enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"
    OVERRIDDEN = "OVERRIDDEN"


class VerificationReport(Base):
    __tablename__ = "verification_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("claim_reviews.id", ondelete="RESTRICT"), nullable=False)
    verdict: Mapped[VerdictEnum] = mapped_column(Enum(VerdictEnum, name="verdictenum"), nullable=False)
    encrypted_analysis: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    llm_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    llm_model_version: Mapped[str] = mapped_column(String(128), nullable=False)
    discrepancy_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

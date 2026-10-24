import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ReviewStatus(str, enum.Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    IN_REVIEW = "IN_REVIEW"
    EVIDENCE_NEEDED = "EVIDENCE_NEEDED"
    ESCALATED = "ESCALATED"
    CLOSED_RESOLVED = "CLOSED_RESOLVED"
    CLOSED_UNRESOLVED = "CLOSED_UNRESOLVED"


class ClaimReview(Base):
    __tablename__ = "claim_reviews"
    __table_args__ = (
        CheckConstraint("severity IS NULL OR (severity >= 1 AND severity <= 5)", name="ck_severity_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    complaint_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="RESTRICT"), nullable=False)
    adjuster_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[ReviewStatus] = mapped_column(Enum(ReviewStatus, name="reviewstatus"), nullable=False, default=ReviewStatus.PENDING_REVIEW)
    encrypted_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    evidence_items: Mapped[list["EvidenceItem"]] = relationship("EvidenceItem", back_populates="review", cascade="all, delete-orphan", order_by="EvidenceItem.sort_order")


class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("claim_reviews.id", ondelete="CASCADE"), nullable=False)
    encrypted_content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    adjuster_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    review: Mapped["ClaimReview"] = relationship("ClaimReview", back_populates="evidence_items")

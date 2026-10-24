import uuid
from datetime import date, datetime, timezone
from sqlalchemy import Boolean, Date, DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
import enum


class ComplaintStatus(str, enum.Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    IN_REVIEW = "IN_REVIEW"
    ESCALATED = "ESCALATED"
    CLOSED_RESOLVED = "CLOSED_RESOLVED"
    CLOSED_UNRESOLVED = "CLOSED_UNRESOLVED"


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    encrypted_narrative: Mapped[str] = mapped_column(Text, nullable=False)
    facility_name: Mapped[str] = mapped_column(String(255), nullable=False)
    incident_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[ComplaintStatus] = mapped_column(
        Enum(ComplaintStatus, name="complaintstatus"),
        nullable=False,
        default=ComplaintStatus.PENDING_REVIEW,
    )
    has_attachments: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

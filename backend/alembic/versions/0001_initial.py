"""Initial schema — all 5 tables

Revision ID: 0001
Revises:
Create Date: 2026-01-01 00:00:00.000000
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ENUM types
    complaint_status = sa.Enum(
        "PENDING_REVIEW", "IN_REVIEW", "ESCALATED", "CLOSED_RESOLVED",
        "CLOSED_UNRESOLVED", name="complaintstatus"
    )
    review_status = sa.Enum(
        "PENDING_REVIEW", "IN_REVIEW", "EVIDENCE_NEEDED", "ESCALATED",
        "CLOSED_RESOLVED", "CLOSED_UNRESOLVED", name="reviewstatus"
    )
    verdict_enum = sa.Enum(
        "PASS", "FAIL", "NEEDS_HUMAN_REVIEW", "OVERRIDDEN", name="verdictenum"
    )

    op.create_table(
        "complaints",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("encrypted_narrative", sa.Text(), nullable=False),
        sa.Column("facility_name", sa.String(length=255), nullable=False),
        sa.Column("incident_date", sa.Date(), nullable=True),
        sa.Column("status", complaint_status, nullable=False, server_default="PENDING_REVIEW"),
        sa.Column("has_attachments", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_complaints_created_at", "complaints", ["created_at"])
    op.create_index("ix_complaints_status", "complaints", ["status"])

    op.create_table(
        "claim_reviews",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("complaint_id", sa.UUID(), nullable=False),
        sa.Column("adjuster_id", sa.UUID(), nullable=False),
        sa.Column("status", review_status, nullable=False, server_default="PENDING_REVIEW"),
        sa.Column("encrypted_summary", sa.Text(), nullable=True),
        sa.Column("severity", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["complaint_id"], ["complaints.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("severity IS NULL OR (severity >= 1 AND severity <= 5)", name="ck_severity_range"),
    )
    op.create_index("ix_claim_reviews_adjuster_id", "claim_reviews", ["adjuster_id"])
    op.create_index("ix_claim_reviews_complaint_id", "claim_reviews", ["complaint_id"])

    op.create_table(
        "evidence_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("review_id", sa.UUID(), nullable=False),
        sa.Column("encrypted_content", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column("adjuster_confirmed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["review_id"], ["claim_reviews.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evidence_items_review_id", "evidence_items", ["review_id"])

    op.create_table(
        "verification_reports",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("review_id", sa.UUID(), nullable=False),
        sa.Column("verdict", verdict_enum, nullable=False),
        sa.Column("encrypted_analysis", sa.Text(), nullable=False),
        sa.Column("encrypted_override_reason", sa.Text(), nullable=True),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("llm_provider", sa.String(length=64), nullable=False),
        sa.Column("llm_model_version", sa.String(length=128), nullable=False),
        sa.Column("discrepancy_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["review_id"], ["claim_reviews.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_verification_reports_review_id", "verification_reports", ["review_id"])
    op.create_index("ix_verification_reports_created_at", "verification_reports", ["created_at"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.UUID(), nullable=True),
        sa.Column("ip_address_hashed", sa.String(length=64), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_resource_id", "audit_logs", ["resource_id"])

    # Production hardening note (apply manually after first deploy):
    # REVOKE UPDATE, DELETE ON TABLE audit_logs FROM advocacy_app_role;
    # REVOKE UPDATE, DELETE ON TABLE verification_reports FROM advocacy_app_role;


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("verification_reports")
    op.drop_table("evidence_items")
    op.drop_table("claim_reviews")
    op.drop_table("complaints")
    sa.Enum(name="verdictenum").drop(op.get_bind())
    sa.Enum(name="reviewstatus").drop(op.get_bind())
    sa.Enum(name="complaintstatus").drop(op.get_bind())

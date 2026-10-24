import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.audit.models import AuditLog

VALID_ACTIONS = {
    "CREATE_COMPLAINT",
    "VIEW_COMPLAINT_PHI",
    "CREATE_REVIEW",
    "VIEW_REVIEW",
    "UPDATE_SUMMARY",
    "UPDATE_STATUS",
    "ADD_EVIDENCE",
    "CONFIRM_EVIDENCE",
    "REORDER_EVIDENCE",
    "RUN_VERIFICATION",
    "OVERRIDE_VERIFICATION",
    "VIEW_VERIFICATION",
    "CREATE_ADJUSTER",
    "LOGIN_ADJUSTER",
}


async def write_audit_log(
    db: AsyncSession,
    action: str,
    resource_type: str,
    actor_id: Optional[uuid.UUID] = None,
    resource_id: Optional[uuid.UUID] = None,
    ip_address_hashed: Optional[str] = None,
    detail: Optional[str] = None,
) -> AuditLog:
    """INSERT-only audit log. No UPDATE or DELETE is ever called on this table."""
    log = AuditLog(
        action=action,
        actor_id=actor_id,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address_hashed=ip_address_hashed,
        detail=detail,
    )
    db.add(log)
    await db.flush()
    return log

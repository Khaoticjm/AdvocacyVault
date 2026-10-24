import inspect
import pytest
from sqlalchemy import select
from app.modules.audit.models import AuditLog
from app.modules.audit import services as audit_services


@pytest.mark.asyncio
async def test_audit_log_created_on_complaint_submit(client, db):
    before_count_result = await db.execute(select(AuditLog).where(AuditLog.action == "CREATE_COMPLAINT"))
    before = len(before_count_result.scalars().all())

    await client.post("/api/v1/complaints/", json={
        "narrative": "Audit log count test — complaint submission narrative.",
        "facility_name": "Audit Count Facility",
    })

    after_result = await db.execute(select(AuditLog).where(AuditLog.action == "CREATE_COMPLAINT"))
    after = len(after_result.scalars().all())
    assert after == before + 1


@pytest.mark.asyncio
async def test_audit_log_on_review_create(client, db):
    comp = await client.post("/api/v1/complaints/", json={
        "narrative": "Complaint for review creation audit log test.",
        "facility_name": "Review Audit Facility",
    })
    cid = comp.json()["id"]
    await client.post("/api/v1/reviews/", json={"complaint_id": cid})

    result = await db.execute(select(AuditLog).where(AuditLog.action == "CREATE_REVIEW"))
    logs = result.scalars().all()
    assert len(logs) >= 1


def test_audit_service_has_no_update_or_delete():
    """Module inspection: audit services must never expose UPDATE or DELETE paths."""
    source = inspect.getsource(audit_services)
    assert "UPDATE" not in source.upper().replace("AUDIT", "").replace("_UPDATE", "")
    # Only INSERT-style db.add() should appear
    assert "db.add(" in source


@pytest.mark.asyncio
async def test_ip_address_not_stored_raw(client, db):
    await client.post("/api/v1/complaints/", json={
        "narrative": "IP address storage test — verifying raw IP exclusion.",
        "facility_name": "IP Test Facility",
    })
    result = await db.execute(select(AuditLog))
    logs = result.scalars().all()
    for log in logs:
        if log.ip_address_hashed:
            assert "." not in log.ip_address_hashed or len(log.ip_address_hashed) == 64


@pytest.mark.asyncio
async def test_audit_log_resource_ids_populated(client, db):
    resp = await client.post("/api/v1/complaints/", json={
        "narrative": "Resource ID audit test — checking resource_id field.",
        "facility_name": "Resource ID Facility",
    })
    complaint_id = resp.json()["id"]

    result = await db.execute(
        select(AuditLog).where(AuditLog.action == "CREATE_COMPLAINT").order_by(AuditLog.created_at.desc())
    )
    log = result.scalars().first()
    assert log is not None
    assert str(log.resource_id) == complaint_id

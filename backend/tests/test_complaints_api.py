import pytest
from sqlalchemy import select, text
from app.modules.complaints.models import Complaint
from app.modules.audit.models import AuditLog
from app.security import decrypt_phi


@pytest.mark.asyncio
async def test_submit_complaint_returns_201(client):
    resp = await client.post("/api/v1/complaints/", json={
        "narrative": "Staff ignored my pain for over three hours despite repeated requests.",
        "facility_name": "Metro Behavioral Health",
        "incident_date": "2024-03-15",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert "id" in body
    assert body["human_review_pending"] is True


@pytest.mark.asyncio
async def test_narrative_encrypted_in_db(client, db):
    resp = await client.post("/api/v1/complaints/", json={
        "narrative": "UNIQUE_SENTINEL_VALUE_FOR_ENCRYPTION_TEST",
        "facility_name": "Test Facility",
    })
    assert resp.status_code == 201
    complaint_id = resp.json()["id"]
    result = await db.execute(select(Complaint).where(Complaint.id == complaint_id))
    complaint = result.scalar_one()
    assert "UNIQUE_SENTINEL_VALUE" not in complaint.encrypted_narrative
    assert decrypt_phi(complaint.encrypted_narrative) == "UNIQUE_SENTINEL_VALUE_FOR_ENCRYPTION_TEST"


@pytest.mark.asyncio
async def test_public_list_excludes_phi(client):
    await client.post("/api/v1/complaints/", json={
        "narrative": "PHI that must not appear in list endpoint response.",
        "facility_name": "PHI Test Facility",
    })
    resp = await client.get("/api/v1/complaints/")
    assert resp.status_code == 200
    for item in resp.json():
        assert "narrative" not in item
        assert "encrypted_narrative" not in item
        assert "PHI that must not appear" not in str(item)


@pytest.mark.asyncio
async def test_submit_creates_audit_log(client, db):
    resp = await client.post("/api/v1/complaints/", json={
        "narrative": "Audit log test — narrative for complaint submission.",
        "facility_name": "Audit Test Facility",
    })
    assert resp.status_code == 201
    result = await db.execute(
        select(AuditLog).where(AuditLog.action == "CREATE_COMPLAINT")
    )
    logs = result.scalars().all()
    assert len(logs) >= 1


@pytest.mark.asyncio
async def test_short_narrative_rejected(client):
    resp = await client.post("/api/v1/complaints/", json={
        "narrative": "Too short",
        "facility_name": "Test",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_review_status_no_phi(client):
    resp = await client.post("/api/v1/complaints/", json={
        "narrative": "Another complaint for status check testing purposes.",
        "facility_name": "Status Test Facility",
    })
    complaint_id = resp.json()["id"]
    status_resp = await client.get(f"/api/v1/complaints/{complaint_id}/review-status")
    assert status_resp.status_code == 200
    body = status_resp.json()
    assert "narrative" not in body
    assert "encrypted_narrative" not in body
    assert "status" in body

import pytest
from sqlalchemy import select
from app.modules.adjuster.models import ClaimReview
from app.security import decrypt_phi


async def _make_complaint(client):
    resp = await client.post("/api/v1/complaints/", json={
        "narrative": "Complaint for adjuster workflow testing purposes only.",
        "facility_name": "Adjuster Test Facility",
    })
    return resp.json()["id"]


async def _make_review(client, complaint_id):
    resp = await client.post("/api/v1/reviews/", json={"complaint_id": complaint_id})
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_create_review(client):
    cid = await _make_complaint(client)
    resp = await client.post("/api/v1/reviews/", json={"complaint_id": cid})
    assert resp.status_code == 201
    assert "id" in resp.json()


@pytest.mark.asyncio
async def test_full_review_lifecycle(client):
    cid = await _make_complaint(client)
    rid = await _make_review(client, cid)

    # Update summary
    resp = await client.patch(f"/api/v1/reviews/{rid}/summary", json={"summary": "Patient reported repeated neglect.", "severity": 4})
    assert resp.status_code == 200

    # Add evidence
    resp = await client.post(f"/api/v1/reviews/{rid}/evidence", json={"content": "Medical record note dated 2024-03-15.", "content_type": "medical_record"})
    assert resp.status_code == 201
    evidence_id = resp.json()["id"]

    # Confirm evidence
    resp = await client.patch(f"/api/v1/reviews/{rid}/evidence/{evidence_id}/confirm")
    assert resp.status_code == 200
    assert resp.json()["adjuster_confirmed"] is True


@pytest.mark.asyncio
async def test_summary_encrypted_in_db(client, db):
    cid = await _make_complaint(client)
    rid = await _make_review(client, cid)
    summary_text = "SUMMARY_SENTINEL_ENCRYPTION_CHECK"
    await client.patch(f"/api/v1/reviews/{rid}/summary", json={"summary": summary_text, "severity": 3})

    result = await db.execute(select(ClaimReview).where(ClaimReview.id == rid))
    review = result.scalar_one()
    assert summary_text not in review.encrypted_summary
    assert decrypt_phi(review.encrypted_summary) == summary_text


@pytest.mark.asyncio
async def test_escalation_lock1_unconfirmed_evidence(client):
    """Lock 1: escalation blocked when evidence is unconfirmed."""
    cid = await _make_complaint(client)
    rid = await _make_review(client, cid)
    await client.post(f"/api/v1/reviews/{rid}/evidence", json={"content": "Unconfirmed evidence item.", "content_type": "note"})

    resp = await client.patch(f"/api/v1/reviews/{rid}/status", json={"status": "ESCALATED"})
    assert resp.status_code == 422
    assert "confirmed" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_escalation_lock2_no_verification(client):
    """Lock 2: escalation blocked when no verification report exists."""
    cid = await _make_complaint(client)
    rid = await _make_review(client, cid)
    # No evidence → lock 1 passes (nothing to confirm), lock 2 fires

    resp = await client.patch(f"/api/v1/reviews/{rid}/status", json={"status": "ESCALATED"})
    assert resp.status_code == 422
    assert "verification" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_valid_status_transitions(client):
    cid = await _make_complaint(client)
    rid = await _make_review(client, cid)
    resp = await client.patch(f"/api/v1/reviews/{rid}/status", json={"status": "EVIDENCE_NEEDED"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "EVIDENCE_NEEDED"


@pytest.mark.asyncio
async def test_evidence_reorder(client):
    cid = await _make_complaint(client)
    rid = await _make_review(client, cid)

    id1 = (await client.post(f"/api/v1/reviews/{rid}/evidence", json={"content": "First item content.", "content_type": "note"})).json()["id"]
    id2 = (await client.post(f"/api/v1/reviews/{rid}/evidence", json={"content": "Second item content.", "content_type": "note"})).json()["id"]

    resp = await client.patch(f"/api/v1/reviews/{rid}/evidence/reorder", json={"ordered_ids": [id2, id1]})
    assert resp.status_code == 200
    orders = {item["id"]: item["sort_order"] for item in resp.json()}
    assert orders[id2] < orders[id1]

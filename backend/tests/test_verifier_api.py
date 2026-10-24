import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import select
from app.modules.verifier.models import VerificationReport, VerdictEnum
from app.security import decrypt_phi


PASS_RESULT = {"verdict": "PASS", "discrepancy_count": 0, "discrepancies": [], "summary": "Evidence is consistent."}
FAIL_RESULT = {"verdict": "FAIL", "discrepancy_count": 4, "discrepancies": [{"type": "gap", "description": "Missing timeline."}], "summary": "Major gaps found."}
NEEDS_HUMAN_RESULT = {"verdict": "NEEDS_HUMAN_REVIEW", "discrepancy_count": 2, "discrepancies": [], "summary": "Ambiguous."}


async def _setup_review_with_confirmed_evidence(client):
    comp = await client.post("/api/v1/complaints/", json={
        "narrative": "Verifier test complaint with sufficient detail for review.",
        "facility_name": "Verifier Test Facility",
    })
    cid = comp.json()["id"]
    rev = await client.post("/api/v1/reviews/", json={"complaint_id": cid})
    rid = rev.json()["id"]
    ev = await client.post(f"/api/v1/reviews/{rid}/evidence", json={"content": "Medical record confirming injury on admission date.", "content_type": "medical_record"})
    eid = ev.json()["id"]
    await client.patch(f"/api/v1/reviews/{rid}/evidence/{eid}/confirm")
    await client.patch(f"/api/v1/reviews/{rid}/summary", json={"summary": "Patient sustained injury during admission.", "severity": 4})
    return rid


@pytest.mark.asyncio
async def test_verification_pass(client):
    rid = await _setup_review_with_confirmed_evidence(client)
    with patch("app.modules.verifier.services._call_llm_blocking", return_value=PASS_RESULT):
        resp = await client.post(f"/api/v1/reviews/{rid}/verify")
    assert resp.status_code == 201
    body = resp.json()
    assert body["verdict"] == "PASS"
    assert body["discrepancy_count"] == 0
    assert body["llm_provider"] == "anthropic"
    assert body["llm_model_version"] == "claude-sonnet-4-6"


@pytest.mark.asyncio
async def test_verification_fail(client):
    rid = await _setup_review_with_confirmed_evidence(client)
    with patch("app.modules.verifier.services._call_llm_blocking", return_value=FAIL_RESULT):
        resp = await client.post(f"/api/v1/reviews/{rid}/verify")
    assert resp.status_code == 201
    assert resp.json()["verdict"] == "FAIL"


@pytest.mark.asyncio
async def test_verification_needs_human(client):
    rid = await _setup_review_with_confirmed_evidence(client)
    with patch("app.modules.verifier.services._call_llm_blocking", return_value=NEEDS_HUMAN_RESULT):
        resp = await client.post(f"/api/v1/reviews/{rid}/verify")
    assert resp.status_code == 201
    assert resp.json()["verdict"] == "NEEDS_HUMAN_REVIEW"


@pytest.mark.asyncio
async def test_analysis_encrypted_in_db(client, db):
    rid = await _setup_review_with_confirmed_evidence(client)
    with patch("app.modules.verifier.services._call_llm_blocking", return_value=PASS_RESULT):
        resp = await client.post(f"/api/v1/reviews/{rid}/verify")
    report_id = resp.json()["id"]
    result = await db.execute(select(VerificationReport).where(VerificationReport.id == report_id))
    report = result.scalar_one()
    assert "PASS" not in report.encrypted_analysis
    assert "consistent" not in report.encrypted_analysis
    decoded = json.loads(decrypt_phi(report.encrypted_analysis))
    assert decoded["verdict"] == "PASS"


@pytest.mark.asyncio
async def test_llm_error_graceful_degradation(client):
    rid = await _setup_review_with_confirmed_evidence(client)
    with patch("app.modules.verifier.services._call_llm_blocking", side_effect=Exception("LLM unavailable")):
        resp = await client.post(f"/api/v1/reviews/{rid}/verify")
    assert resp.status_code == 201
    assert resp.json()["verdict"] == "NEEDS_HUMAN_REVIEW"


@pytest.mark.asyncio
async def test_override_requires_justification(client):
    rid = await _setup_review_with_confirmed_evidence(client)
    with patch("app.modules.verifier.services._call_llm_blocking", return_value=FAIL_RESULT):
        verify_resp = await client.post(f"/api/v1/reviews/{rid}/verify")
    report_id = verify_resp.json()["id"]

    resp = await client.post(f"/api/v1/verifications/{report_id}/override", json={"justification": "Short"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_override_success(client):
    rid = await _setup_review_with_confirmed_evidence(client)
    with patch("app.modules.verifier.services._call_llm_blocking", return_value=FAIL_RESULT):
        verify_resp = await client.post(f"/api/v1/reviews/{rid}/verify")
    report_id = verify_resp.json()["id"]

    resp = await client.post(f"/api/v1/verifications/{report_id}/override", json={
        "justification": "Additional documentation reviewed outside system confirms evidence validity."
    })
    assert resp.status_code == 200
    assert resp.json()["verdict"] == "OVERRIDDEN"


@pytest.mark.asyncio
async def test_double_override_rejected(client):
    rid = await _setup_review_with_confirmed_evidence(client)
    with patch("app.modules.verifier.services._call_llm_blocking", return_value=FAIL_RESULT):
        verify_resp = await client.post(f"/api/v1/reviews/{rid}/verify")
    report_id = verify_resp.json()["id"]

    await client.post(f"/api/v1/verifications/{report_id}/override", json={
        "justification": "First override with sufficient justification text here."
    })
    resp = await client.post(f"/api/v1/verifications/{report_id}/override", json={
        "justification": "Second override attempt should be rejected by the system."
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_eu_ai_act_model_identity_in_response(client):
    """EU AI Act Art.13: LLM identity must appear in every verification response."""
    rid = await _setup_review_with_confirmed_evidence(client)
    with patch("app.modules.verifier.services._call_llm_blocking", return_value=PASS_RESULT):
        resp = await client.post(f"/api/v1/reviews/{rid}/verify")
    body = resp.json()
    assert body["llm_provider"]
    assert body["llm_model_version"]


@pytest.mark.asyncio
async def test_public_verification_history_no_phi(client):
    rid = await _setup_review_with_confirmed_evidence(client)
    with patch("app.modules.verifier.services._call_llm_blocking", return_value=PASS_RESULT):
        await client.post(f"/api/v1/reviews/{rid}/verify")

    resp = await client.get(f"/api/v1/reviews/{rid}/verifications")
    assert resp.status_code == 200
    for item in resp.json():
        assert "analysis" not in item
        assert "encrypted_analysis" not in item

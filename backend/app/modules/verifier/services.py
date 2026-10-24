import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.modules.adjuster.models import ClaimReview
from app.modules.adjuster.services import compute_input_hash
from app.modules.verifier.models import VerificationReport, VerdictEnum
from app.security import decrypt_phi, encrypt_phi
from app.modules.audit.services import write_audit_log

ADVERSARIAL_SYSTEM_PROMPT = """You are an independent verification auditor for a healthcare complaint system.
Your role is to audit evidence packages for consistency, completeness, and potential issues.

CRITICAL RULES:
1. You are adversarial — assume documents may be incomplete or inconsistent.
2. Identify any discrepancies, missing information, or unsupported claims.
3. Return ONLY valid JSON in the exact format specified. No prose outside the JSON.
4. Never trust the adjuster's conclusions — derive your own from the raw evidence.
5. Discrepancy count must accurately reflect the number of distinct issues found.

Return this exact JSON structure:
{
  "verdict": "PASS" | "FAIL" | "NEEDS_HUMAN_REVIEW",
  "discrepancy_count": <integer>,
  "discrepancies": [{"type": str, "description": str}],
  "summary": str
}

PASS = evidence is consistent and complete.
FAIL = clear inconsistencies or missing critical information.
NEEDS_HUMAN_REVIEW = ambiguous; a human must decide.
"""


async def _call_llm(prompt: str) -> dict[str, Any]:
    """Call the configured verifier LLM. Returns parsed JSON dict."""
    provider = settings.verifier_llm_provider.lower()

    if provider == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=settings.verifier_llm_api_key)
        msg = client.messages.create(
            model=settings.verifier_llm_model,
            max_tokens=1024,
            temperature=0,
            system=ADVERSARIAL_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text
    elif provider == "openai":
        import openai
        client = openai.OpenAI(api_key=settings.verifier_llm_api_key)
        resp = client.chat.completions.create(
            model=settings.verifier_llm_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": ADVERSARIAL_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        raw = resp.choices[0].message.content
    else:
        raise ValueError(f"Unknown verifier LLM provider: {provider}")

    return json.loads(raw)


def _derive_verdict(result: dict, discrepancy_count: int) -> VerdictEnum:
    """Derive verdict from discrepancy count, not from LLM trust."""
    if discrepancy_count == 0:
        return VerdictEnum.PASS
    if discrepancy_count >= 3:
        return VerdictEnum.FAIL
    return VerdictEnum.NEEDS_HUMAN_REVIEW


async def run_verification(
    db: AsyncSession,
    review: ClaimReview,
    actor_id: uuid.UUID,
) -> VerificationReport:
    from sqlalchemy.orm import selectinload as sload
    from sqlalchemy import select as sa_select
    result = await db.execute(
        sa_select(ClaimReview).options(sload(ClaimReview.evidence_items)).where(ClaimReview.id == review.id)
    )
    review = result.scalar_one()

    evidence_texts = [
        decrypt_phi(e.encrypted_content)
        for e in sorted(review.evidence_items, key=lambda x: x.sort_order)
    ]
    prompt = "Evidence package for review:\n\n" + "\n\n---\n\n".join(
        f"[Item {i+1}]\n{text}" for i, text in enumerate(evidence_texts)
    )

    input_hash = compute_input_hash(review)

    try:
        llm_result = await _call_llm.__wrapped__(prompt) if hasattr(_call_llm, "__wrapped__") else await _call_llm_sync(prompt)
    except Exception as exc:
        llm_result = {
            "verdict": "NEEDS_HUMAN_REVIEW",
            "discrepancy_count": 1,
            "discrepancies": [{"type": "llm_error", "description": str(exc)}],
            "summary": "Verification LLM call failed; human review required.",
        }

    discrepancy_count = int(llm_result.get("discrepancy_count", 0))
    verdict = _derive_verdict(llm_result, discrepancy_count)

    report = VerificationReport(
        review_id=review.id,
        verdict=verdict,
        encrypted_analysis=encrypt_phi(json.dumps(llm_result)),
        input_hash=input_hash,
        llm_provider=settings.verifier_llm_provider,
        llm_model_version=settings.verifier_llm_model,
        discrepancy_count=discrepancy_count,
    )
    db.add(report)
    await db.flush()
    await write_audit_log(db, action="RUN_VERIFICATION", actor_id=actor_id, resource_type="verification_report", resource_id=report.id)
    return report


async def _call_llm_sync(prompt: str) -> dict[str, Any]:
    """Sync wrapper for non-async LLM clients."""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: _call_llm_blocking(prompt))


def _call_llm_blocking(prompt: str) -> dict[str, Any]:
    provider = settings.verifier_llm_provider.lower()
    if provider == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=settings.verifier_llm_api_key)
        msg = client.messages.create(
            model=settings.verifier_llm_model,
            max_tokens=1024,
            temperature=0,
            system=ADVERSARIAL_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text
    elif provider == "openai":
        import openai
        client = openai.OpenAI(api_key=settings.verifier_llm_api_key)
        resp = client.chat.completions.create(
            model=settings.verifier_llm_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": ADVERSARIAL_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        raw = resp.choices[0].message.content
    else:
        raise ValueError(f"Unknown verifier LLM provider: {provider}")
    return json.loads(raw)


async def create_override(
    db: AsyncSession,
    report: VerificationReport,
    justification: str,
    actor_id: uuid.UUID,
) -> VerificationReport:
    if report.verdict == VerdictEnum.OVERRIDDEN:
        raise ValueError("This report has already been overridden.")
    report.encrypted_override_reason = encrypt_phi(justification)
    report.verdict = VerdictEnum.OVERRIDDEN
    await db.flush()
    await write_audit_log(db, action="OVERRIDE_VERIFICATION", actor_id=actor_id, resource_type="verification_report", resource_id=report.id)
    return report


async def get_latest_report(db: AsyncSession, review_id: uuid.UUID) -> VerificationReport | None:
    result = await db.execute(
        select(VerificationReport)
        .where(VerificationReport.review_id == review_id)
        .order_by(VerificationReport.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def list_reports(db: AsyncSession, review_id: uuid.UUID):
    result = await db.execute(
        select(VerificationReport)
        .where(VerificationReport.review_id == review_id)
        .order_by(VerificationReport.created_at.desc())
    )
    return list(result.scalars().all())

# Advocacy Vault

> HIPAA · WCAG 2.2 AA · EU AI Act Art. 13/14 compliant  
> Crowdsourced healthcare complaint tracking with AI-assisted, human-reviewed adjudication.

---

## What It Does

Advocacy Vault provides a secure, accessible channel for patients to document healthcare complaints. Every submission is:

- **Field-level encrypted** (Fernet AES-128-CBC + HMAC-SHA256) before touching the database
- **Routed to a human adjuster** who controls all decisions — the AI only assists
- **Verified by a dual-LLM adversarial check** (primary and verifier must be different models, enforced at boot)
- **Gated by a three-lock escalation system** before any complaint can be escalated

---

## Architecture

```
nginx (TLS, rate-limiting)
    │
    ├── Reflex frontend  :3000  →  / · /dashboard · /adjuster
    └── FastAPI backend  :8001  →  /api/v1/...
              │
         PostgreSQL 15
```

### Backend modules

| Module | Purpose |
|---|---|
| `complaints` | Public submission endpoint; encrypts narrative + audits |
| `adjuster` | Claim review workflow; three-lock escalation gate |
| `verifier` | Dual-LLM adversarial verification; override with justification |
| `audit` | INSERT-only audit log; no UPDATE/DELETE paths |
| `anonymizer` | EXIF scrubbing (GPS IFD + DateTimeOriginal zeroed) |

---

## Privacy & Security Design

| Concern | Mechanism |
|---|---|
| PHI at rest | Fernet field-level encryption on 5 DB columns |
| Raw IP addresses | Never stored; HMAC-SHA256 keyed hash only |
| Image metadata | piexif zeros GPS IFD + DateTimeOriginal before persistence |
| Audit tampering | INSERT-only table; no FK; no UPDATE/DELETE ever exposed |
| AI identity | `llm_provider` + `llm_model_version` on every VerificationReport |
| Human override | Requires ≥ 20 char written justification; logged in audit trail |
| LLM model diversity | Config validation raises at boot if primary == verifier model |

---

## EU AI Act Compliance (Art. 13 / 14)

- **Disclosure modal** gates every complaint submission — users must acknowledge AI involvement before submitting
- **LLM identity** (provider + model version) stored on every verification report and returned to the adjuster UI
- **Human adjuster** reviews every AI determination; no automated adverse decisions
- **Override pathway** exists and requires written justification (≥ 20 chars)

---

## WCAG 2.2 AA Compliance

- All form fields have visible, programmatically associated labels
- Focus indicators: `outline: 2px solid #E39B42` on all interactive elements
- ARIA roles: `role="dialog" aria-modal="true"` on disclosure modal; `role="alert"` on error messages
- Skip-to-content link for keyboard users
- Colour contrast: amber `#E39B42` on dark `#0E0F10` (passes AA for large text)

---

## Quick Start (Docker Compose)

### 1. Copy env file and fill in secrets

```bash
cp backend/.env.example backend/.env
# Edit backend/.env:
#   PHI_ENCRYPTION_KEY  — generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
#   JWT_SECRET_KEY      — generate: openssl rand -hex 32
#   IP_HASH_SALT        — generate: openssl rand -hex 32
#   PRIMARY_LLM_MODEL   — e.g. claude-sonnet-4-6
#   VERIFIER_LLM_MODEL  — must differ from PRIMARY, e.g. gpt-4o
#   VERIFIER_LLM_API_KEY — your OpenAI/Anthropic key for the verifier
```

### 2. Start services

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Submit complaint | http://localhost:3000/ |
| Dashboard | http://localhost:3000/dashboard |
| Adjuster workbench | http://localhost:3000/adjuster |
| API docs (Swagger) | http://localhost:8001/docs |

### 3. Run backend tests

```bash
cd backend
pip install -r requirements.txt
pytest -v
```

---

## Project Structure

```
advocacyvault/
├── docker-compose.yml
├── nginx.conf
├── backend/
│   ├── Dockerfile.backend
│   ├── requirements.txt
│   ├── .env.example
│   ├── alembic/
│   │   └── versions/0001_initial.py
│   ├── app/
│   │   ├── config.py          # Pydantic settings; dual-LLM validation
│   │   ├── main.py            # FastAPI app; CORS; security headers
│   │   ├── security.py        # Fernet encrypt/decrypt; JWT; bcrypt; IP hash
│   │   └── modules/
│   │       ├── complaints/    # Submission endpoint
│   │       ├── adjuster/      # Claim review + three-lock escalation
│   │       ├── verifier/      # Dual-LLM adversarial check
│   │       ├── audit/         # INSERT-only audit log
│   │       └── anonymizer/    # EXIF scrubber
│   └── tests/
│       ├── conftest.py
│       ├── test_security.py       # 20 tests
│       ├── test_complaints_api.py # 6 tests
│       ├── test_adjuster_api.py   # 8 tests
│       ├── test_verifier_api.py   # 10 tests
│       ├── test_audit_log.py      # 5 tests
│       └── test_anonymizer.py     # 6 tests
└── frontend/
    ├── Dockerfile.frontend
    ├── requirements.txt
    ├── rxconfig.py
    └── frontend/
        ├── frontend.py            # Reflex app entry point
        ├── components/
        │   ├── accessible_inputs.py   # WCAG 2.2 AA form components
        │   └── disclosure_modal.py    # EU AI Act Art. 13/14 gate
        └── views/
            ├── submit_complaint.py    # Route: /
            ├── dashboard.py           # Route: /dashboard
            └── adjuster_workbench.py  # Route: /adjuster
```

---

## API Reference

Full interactive docs at `/docs` (Swagger UI) and `/redoc` when backend is running.

### Key endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/complaints/` | Submit complaint (narrative encrypted) |
| `GET` | `/api/v1/complaints/` | Public list (no PHI) |
| `GET` | `/api/v1/complaints/{id}/review-status` | Status check (no PHI) |
| `POST` | `/api/v1/reviews/` | Create claim review |
| `PATCH` | `/api/v1/reviews/{id}/summary` | Update adjuster summary |
| `POST` | `/api/v1/reviews/{id}/evidence` | Add evidence item |
| `PATCH` | `/api/v1/reviews/{id}/evidence/{eid}/confirm` | Confirm evidence (lock 1) |
| `POST` | `/api/v1/reviews/{id}/verify` | Run LLM verification (lock 2) |
| `POST` | `/api/v1/verifications/{id}/override` | Override with justification |
| `PATCH` | `/api/v1/reviews/{id}/status` | Status transition (escalation gated) |

---

## Rate Limiting (nginx)

| Zone | Limit |
|---|---|
| General | 60 req/min |
| Complaints | 10 req/min |
| Verification | 2 req/min |

---

## Pairing with iwalkedin.com

Once deployed, a "File a Complaint" section can be embedded directly in the iwalkedin.com landing page using an `<iframe>` or a styled link to the live Advocacy Vault URL. The dark theme (`#0E0F10` background, `#E39B42` amber accent, Oswald/Source Serif 4/IBM Plex Mono fonts) matches iwalkedin.com exactly for seamless visual integration.

---

## License

Proprietary — Sphinx Global Enterprises Corp. All rights reserved.

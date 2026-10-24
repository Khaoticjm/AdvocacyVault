"""
Adjuster Workbench — route: /adjuster
Internal review interface. Three-lock escalation gate enforced by backend.
"""
import httpx
import reflex as rx
from ..components.accessible_inputs import labeled_textarea, labeled_input, accessible_button

API_BASE = "http://backend:8001/api/v1"


class AdjusterState(rx.State):
    # Review list
    reviews: list[dict] = []
    is_loading_reviews: bool = True

    # Selected review
    selected_review_id: str = ""
    selected_review: dict = {}
    evidence_items: list[dict] = []
    verifications: list[dict] = []

    # Summary form
    summary_text: str = ""
    severity: str = "3"

    # Evidence form
    new_evidence_content: str = ""
    new_evidence_type: str = "note"

    # Override form
    override_justification: str = ""

    # Complaint lookup
    lookup_complaint_id: str = ""

    # UI
    error: str = ""
    success_msg: str = ""
    is_submitting: bool = False

    async def load_reviews(self):
        self.is_loading_reviews = True
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(f"{API_BASE}/reviews/")
            if resp.status_code == 200:
                self.reviews = resp.json()
        except Exception as exc:
            self.error = f"Failed to load reviews: {exc}"
        finally:
            self.is_loading_reviews = False

    async def select_review(self, review_id: str):
        self.selected_review_id = review_id
        self.error = ""
        self.success_msg = ""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r1 = await client.get(f"{API_BASE}/reviews/{review_id}")
                r2 = await client.get(f"{API_BASE}/reviews/{review_id}/evidence")
                r3 = await client.get(f"{API_BASE}/reviews/{review_id}/verifications")
            if r1.status_code == 200:
                self.selected_review = r1.json()
                self.summary_text = self.selected_review.get("summary", "") or ""
            self.evidence_items = r2.json() if r2.status_code == 200 else []
            self.verifications = r3.json() if r3.status_code == 200 else []
        except Exception as exc:
            self.error = f"Load failed: {exc}"

    async def save_summary(self):
        if not self.selected_review_id:
            return
        self.is_submitting = True
        self.error = ""
        try:
            sev = int(self.severity)
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.patch(
                    f"{API_BASE}/reviews/{self.selected_review_id}/summary",
                    json={"summary": self.summary_text, "severity": sev},
                )
            if resp.status_code == 200:
                self.success_msg = "Summary saved."
                self.selected_review = resp.json()
            else:
                self.error = resp.json().get("detail", "Save failed.")
        except Exception as exc:
            self.error = f"Save failed: {exc}"
        finally:
            self.is_submitting = False

    async def add_evidence(self):
        if not self.selected_review_id or not self.new_evidence_content.strip():
            return
        self.is_submitting = True
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{API_BASE}/reviews/{self.selected_review_id}/evidence",
                    json={
                        "content": self.new_evidence_content.strip(),
                        "content_type": self.new_evidence_type,
                    },
                )
            if resp.status_code == 201:
                self.evidence_items = [*self.evidence_items, resp.json()]
                self.new_evidence_content = ""
                self.success_msg = "Evidence added."
            else:
                self.error = resp.json().get("detail", "Add evidence failed.")
        except Exception as exc:
            self.error = f"Add evidence failed: {exc}"
        finally:
            self.is_submitting = False

    async def confirm_evidence(self, evidence_id: str):
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.patch(
                    f"{API_BASE}/reviews/{self.selected_review_id}/evidence/{evidence_id}/confirm"
                )
            if resp.status_code == 200:
                updated = resp.json()
                self.evidence_items = [
                    updated if e["id"] == evidence_id else e
                    for e in self.evidence_items
                ]
                self.success_msg = "Evidence confirmed."
            else:
                self.error = resp.json().get("detail", "Confirm failed.")
        except Exception as exc:
            self.error = f"Confirm failed: {exc}"

    async def run_verification(self):
        if not self.selected_review_id:
            return
        self.is_submitting = True
        self.error = ""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{API_BASE}/reviews/{self.selected_review_id}/verify"
                )
            if resp.status_code == 201:
                self.verifications = [resp.json(), *self.verifications]
                self.success_msg = f"Verification complete: {resp.json().get('verdict')}"
            else:
                self.error = resp.json().get("detail", "Verification failed.")
        except Exception as exc:
            self.error = f"Verification failed: {exc}"
        finally:
            self.is_submitting = False

    async def override_verdict(self, report_id: str):
        if len(self.override_justification.strip()) < 20:
            self.error = "Justification must be at least 20 characters."
            return
        self.is_submitting = True
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{API_BASE}/verifications/{report_id}/override",
                    json={"justification": self.override_justification.strip()},
                )
            if resp.status_code == 200:
                self.override_justification = ""
                self.success_msg = "Override recorded."
                # Refresh verifications
                async with httpx.AsyncClient(timeout=15.0) as client:
                    r = await client.get(
                        f"{API_BASE}/reviews/{self.selected_review_id}/verifications"
                    )
                self.verifications = r.json() if r.status_code == 200 else self.verifications
            else:
                self.error = resp.json().get("detail", "Override failed.")
        except Exception as exc:
            self.error = f"Override failed: {exc}"
        finally:
            self.is_submitting = False

    async def escalate_review(self):
        if not self.selected_review_id:
            return
        self.is_submitting = True
        self.error = ""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.patch(
                    f"{API_BASE}/reviews/{self.selected_review_id}/status",
                    json={"status": "ESCALATED"},
                )
            if resp.status_code == 200:
                self.selected_review = resp.json()
                self.success_msg = "Review escalated successfully."
            else:
                detail = resp.json().get("detail", "Escalation blocked.")
                self.error = f"Escalation blocked: {detail}"
        except Exception as exc:
            self.error = f"Escalation failed: {exc}"
        finally:
            self.is_submitting = False

    def set_summary_text(self, v: str):
        self.summary_text = v

    def set_severity(self, v: str):
        self.severity = v

    def set_new_evidence_content(self, v: str):
        self.new_evidence_content = v

    def set_new_evidence_type(self, v: str):
        self.new_evidence_type = v

    def set_override_justification(self, v: str):
        self.override_justification = v

    @rx.event
    def on_load(self):
        return AdjusterState.load_reviews


# ── Components ───────────────────────────────────────────────────────────────

def nav() -> rx.Component:
    return rx.el.nav(
        rx.el.a(
            "Advocacy Vault",
            href="/",
            style={
                "font_family": "Oswald, sans-serif",
                "font_size": "1.25rem",
                "font_weight": "700",
                "color": "#E39B42",
                "text_decoration": "none",
            },
        ),
        rx.el.span(
            "Adjuster Workbench",
            style={
                "font_family": "IBM Plex Mono, monospace",
                "font_size": "0.8125rem",
                "color": "#6b7280",
                "background": "rgba(227,155,66,0.1)",
                "border": "1px solid rgba(227,155,66,0.2)",
                "padding": "0.2rem 0.6rem",
                "border_radius": "9999px",
            },
        ),
        style={
            "display": "flex",
            "justify_content": "space-between",
            "align_items": "center",
            "padding": "1rem 1.5rem",
            "border_bottom": "1px solid #1f2937",
            "background": "#0E0F10",
        },
    )


def evidence_card(ev: dict) -> rx.Component:
    return rx.box(
        rx.box(
            rx.el.span(
                ev.get("content_type", "note"),
                style={
                    "font_family": "IBM Plex Mono, monospace",
                    "font_size": "0.7rem",
                    "text_transform": "uppercase",
                    "letter_spacing": "0.1em",
                    "color": "#9ca3af",
                    "background": "#1f2937",
                    "padding": "0.15rem 0.5rem",
                    "border_radius": "9999px",
                },
            ),
            rx.cond(
                ev.get("adjuster_confirmed", False),
                rx.el.span(
                    "✓ Confirmed",
                    style={"font_size": "0.75rem", "color": "#4ade80", "margin_left": "0.5rem"},
                ),
                rx.el.button(
                    "Confirm",
                    on_click=lambda: AdjusterState.confirm_evidence(ev.get("id", "")),
                    style={
                        "font_size": "0.75rem",
                        "color": "#E39B42",
                        "background": "transparent",
                        "border": "1px solid #E39B42",
                        "border_radius": "0.25rem",
                        "padding": "0.1rem 0.5rem",
                        "cursor": "pointer",
                        "margin_left": "0.5rem",
                        "_focus": {"outline": "2px solid #E39B42"},
                    },
                ),
            ),
            style={"display": "flex", "align_items": "center", "margin_bottom": "0.5rem"},
        ),
        rx.el.p(
            ev.get("content", ""),
            style={
                "color": "#d1d5db",
                "font_size": "0.875rem",
                "line_height": "1.5",
                "margin": "0",
            },
        ),
        style={
            "background": "#111214",
            "border": "1px solid #374151",
            "border_radius": "0.375rem",
            "padding": "0.75rem",
            "margin_bottom": "0.5rem",
        },
    )


def verification_card(v: dict) -> rx.Component:
    verdict = v.get("verdict", "")
    verdict_color = {
        "PASS": "#4ade80",
        "FAIL": "#f87171",
        "NEEDS_HUMAN_REVIEW": "#fbbf24",
        "OVERRIDDEN": "#a78bfa",
    }.get(verdict, "#9ca3af")

    return rx.box(
        rx.box(
            rx.el.span(
                verdict,
                style={
                    "font_family": "IBM Plex Mono, monospace",
                    "font_size": "0.8125rem",
                    "font_weight": "700",
                    "color": verdict_color,
                },
            ),
            rx.el.span(
                f" — {v.get('llm_provider','?')}:{v.get('llm_model_version','?')}",
                style={
                    "font_family": "IBM Plex Mono, monospace",
                    "font_size": "0.7rem",
                    "color": "#6b7280",
                    "margin_left": "0.5rem",
                },
            ),
            style={"margin_bottom": "0.5rem"},
        ),
        rx.el.p(
            f"Discrepancies: {v.get('discrepancy_count', 0)}",
            style={"color": "#9ca3af", "font_size": "0.8125rem", "margin": "0 0 0.75rem"},
        ),
        # Override controls (only for FAIL)
        rx.cond(
            verdict == "FAIL",
            rx.box(
                labeled_textarea(
                    label="Override Justification",
                    field_id=f"override_{v.get('id','')}",
                    value=AdjusterState.override_justification,
                    on_change=AdjusterState.set_override_justification,
                    placeholder="Minimum 20 characters. Explain why the AI verdict should be overridden.",
                    min_length=20,
                ),
                accessible_button(
                    label="Override Verdict",
                    on_click=lambda: AdjusterState.override_verdict(v.get("id", "")),
                    variant="secondary",
                    disabled=AdjusterState.is_submitting,
                ),
            ),
            rx.fragment(),
        ),
        style={
            "background": "#111214",
            "border": f"1px solid {verdict_color}33",
            "border_radius": "0.375rem",
            "padding": "0.875rem",
            "margin_bottom": "0.5rem",
        },
    )


def review_detail() -> rx.Component:
    return rx.box(
        rx.el.h2(
            f"Review: {AdjusterState.selected_review_id[:8]}…",
            style={
                "font_family": "Oswald, sans-serif",
                "font_size": "1.125rem",
                "font_weight": "700",
                "color": "#f9fafb",
                "margin_bottom": "1rem",
            },
        ),
        # Messages
        rx.cond(
            AdjusterState.error != "",
            rx.el.div(
                AdjusterState.error,
                role="alert",
                style={
                    "background": "rgba(220,38,38,0.15)",
                    "border": "1px solid #dc2626",
                    "border_radius": "0.375rem",
                    "padding": "0.625rem 1rem",
                    "color": "#fca5a5",
                    "font_size": "0.875rem",
                    "margin_bottom": "1rem",
                },
            ),
            rx.fragment(),
        ),
        rx.cond(
            AdjusterState.success_msg != "",
            rx.el.div(
                AdjusterState.success_msg,
                role="status",
                style={
                    "background": "rgba(74,222,128,0.1)",
                    "border": "1px solid #4ade80",
                    "border_radius": "0.375rem",
                    "padding": "0.625rem 1rem",
                    "color": "#4ade80",
                    "font_size": "0.875rem",
                    "margin_bottom": "1rem",
                },
            ),
            rx.fragment(),
        ),
        # Summary section
        rx.el.h3(
            "Adjuster Summary",
            style={"font_family": "Oswald, sans-serif", "color": "#E39B42", "font_size": "1rem", "margin_bottom": "0.75rem"},
        ),
        labeled_textarea(
            label="Summary",
            field_id="adj_summary",
            value=AdjusterState.summary_text,
            on_change=AdjusterState.set_summary_text,
            placeholder="Summarise your findings…",
        ),
        labeled_input(
            label="Severity (1–5)",
            field_id="severity",
            value=AdjusterState.severity,
            on_change=AdjusterState.set_severity,
            input_type="number",
            helper_text="1 = minor, 5 = critical",
        ),
        accessible_button(
            label="Save Summary",
            on_click=AdjusterState.save_summary,
            disabled=AdjusterState.is_submitting,
        ),
        rx.el.hr(style={"border_color": "#1f2937", "margin": "1.5rem 0"}),
        # Evidence section
        rx.el.h3(
            "Evidence",
            style={"font_family": "Oswald, sans-serif", "color": "#E39B42", "font_size": "1rem", "margin_bottom": "0.75rem"},
        ),
        rx.foreach(AdjusterState.evidence_items, evidence_card),
        labeled_textarea(
            label="Add Evidence",
            field_id="new_evidence",
            value=AdjusterState.new_evidence_content,
            on_change=AdjusterState.set_new_evidence_content,
            placeholder="Paste or type evidence content…",
        ),
        accessible_button(
            label="Add Evidence",
            on_click=AdjusterState.add_evidence,
            variant="secondary",
            disabled=AdjusterState.is_submitting,
        ),
        rx.el.hr(style={"border_color": "#1f2937", "margin": "1.5rem 0"}),
        # Verification section
        rx.el.h3(
            "AI Verification",
            style={"font_family": "Oswald, sans-serif", "color": "#E39B42", "font_size": "1rem", "margin_bottom": "0.75rem"},
        ),
        rx.foreach(AdjusterState.verifications, verification_card),
        accessible_button(
            label="Run Verification",
            on_click=AdjusterState.run_verification,
            variant="secondary",
            disabled=AdjusterState.is_submitting,
        ),
        rx.el.hr(style={"border_color": "#1f2937", "margin": "1.5rem 0"}),
        # Escalation gate
        rx.el.h3(
            "Escalate",
            style={"font_family": "Oswald, sans-serif", "color": "#E39B42", "font_size": "1rem", "margin_bottom": "0.5rem"},
        ),
        rx.el.p(
            "Three-lock gate: (1) all evidence confirmed, (2) latest verification is PASS or OVERRIDDEN, (3) input hash unchanged post-verification.",
            style={"color": "#6b7280", "font_size": "0.8rem", "margin_bottom": "1rem", "font_family": "IBM Plex Mono, monospace"},
        ),
        accessible_button(
            label="Escalate Review",
            on_click=AdjusterState.escalate_review,
            variant="danger",
            disabled=AdjusterState.is_submitting,
        ),
        style={
            "background": "#1a1b1e",
            "border": "1px solid #374151",
            "border_radius": "0.5rem",
            "padding": "1.5rem",
        },
    )


def review_list_panel() -> rx.Component:
    return rx.box(
        rx.el.h2(
            "Open Reviews",
            style={
                "font_family": "Oswald, sans-serif",
                "font_size": "1rem",
                "font_weight": "700",
                "color": "#9ca3af",
                "margin_bottom": "0.75rem",
                "text_transform": "uppercase",
                "letter_spacing": "0.1em",
            },
        ),
        rx.cond(
            AdjusterState.is_loading_reviews,
            rx.el.p("Loading…", style={"color": "#6b7280", "font_size": "0.875rem"}),
            rx.foreach(
                AdjusterState.reviews,
                lambda r: rx.el.button(
                    rx.el.span(
                        r.get("id", "")[:8] + "…",
                        style={"font_family": "IBM Plex Mono, monospace", "font_size": "0.75rem", "display": "block"},
                    ),
                    rx.el.span(
                        r.get("status", ""),
                        style={
                            "font_size": "0.7rem",
                            "color": "#9ca3af",
                            "text_transform": "uppercase",
                            "letter_spacing": "0.05em",
                        },
                    ),
                    on_click=lambda: AdjusterState.select_review(r.get("id", "")),
                    style={
                        "display": "block",
                        "width": "100%",
                        "text_align": "left",
                        "padding": "0.625rem 0.75rem",
                        "background": rx.cond(
                            AdjusterState.selected_review_id == r.get("id", ""),
                            "rgba(227,155,66,0.1)",
                            "transparent",
                        ),
                        "border": "1px solid",
                        "border_color": rx.cond(
                            AdjusterState.selected_review_id == r.get("id", ""),
                            "rgba(227,155,66,0.3)",
                            "#1f2937",
                        ),
                        "border_radius": "0.375rem",
                        "cursor": "pointer",
                        "margin_bottom": "0.375rem",
                        "color": "#e5e7eb",
                        "_focus": {"outline": "2px solid #E39B42"},
                        "_hover": {"background": "rgba(255,255,255,0.03)"},
                    },
                ),
            ),
        ),
        style={
            "background": "#1a1b1e",
            "border": "1px solid #374151",
            "border_radius": "0.5rem",
            "padding": "1rem",
            "min_width": "200px",
            "max_width": "240px",
        },
    )


@rx.page(route="/adjuster", title="Adjuster Workbench — Advocacy Vault", on_load=AdjusterState.on_load)
def adjuster_page() -> rx.Component:
    return rx.box(
        nav(),
        rx.box(
            review_list_panel(),
            rx.cond(
                AdjusterState.selected_review_id != "",
                review_detail(),
                rx.el.p(
                    "← Select a review to begin",
                    style={
                        "color": "#6b7280",
                        "font_family": "IBM Plex Mono, monospace",
                        "font_size": "0.875rem",
                        "padding": "2rem",
                    },
                ),
            ),
            style={
                "display": "flex",
                "gap": "1.5rem",
                "max_width": "1100px",
                "margin": "0 auto",
                "padding": "2rem 1rem",
                "align_items": "flex-start",
            },
        ),
        style={"background": "#0E0F10", "min_height": "100vh"},
    )

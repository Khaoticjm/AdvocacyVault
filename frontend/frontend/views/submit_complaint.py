"""
Submit Complaint view — route: /
EU AI Act disclosure gate → complaint form → confirmation.
"""
import httpx
import reflex as rx
from ..components.accessible_inputs import labeled_input, labeled_textarea, accessible_button
from ..components.disclosure_modal import disclosure_modal

API_BASE = "http://backend:8001/api/v1"


class SubmitState(rx.State):
    # Disclosure gate
    disclosure_accepted: bool = False
    show_disclosure: bool = True

    # Form fields
    narrative: str = ""
    facility_name: str = ""
    incident_date: str = ""
    contact_email: str = ""

    # UI state
    is_submitting: bool = False
    submission_id: str = ""
    error_message: str = ""
    success: bool = False

    def accept_disclosure(self):
        self.disclosure_accepted = True
        self.show_disclosure = False

    def decline_disclosure(self):
        self.show_disclosure = False
        return rx.redirect("/")

    def set_narrative(self, value: str):
        self.narrative = value

    def set_facility_name(self, value: str):
        self.facility_name = value

    def set_incident_date(self, value: str):
        self.incident_date = value

    def set_contact_email(self, value: str):
        self.contact_email = value

    async def handle_submit(self):
        if not self.disclosure_accepted:
            self.error_message = "You must accept the AI disclosure before submitting."
            return

        if len(self.narrative.strip()) < 50:
            self.error_message = "Please provide a more detailed account (at least 50 characters)."
            return

        if not self.facility_name.strip():
            self.error_message = "Facility name is required."
            return

        self.is_submitting = True
        self.error_message = ""

        payload = {
            "narrative": self.narrative.strip(),
            "facility_name": self.facility_name.strip(),
        }
        if self.incident_date:
            payload["incident_date"] = self.incident_date
        if self.contact_email:
            payload["contact_email"] = self.contact_email

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(f"{API_BASE}/complaints/", json=payload)

            if resp.status_code == 201:
                data = resp.json()
                self.submission_id = data["id"]
                self.success = True
                self.narrative = ""
                self.facility_name = ""
                self.incident_date = ""
                self.contact_email = ""
            else:
                detail = resp.json().get("detail", "Submission failed. Please try again.")
                self.error_message = str(detail)
        except Exception as exc:
            self.error_message = f"Network error: {str(exc)}. Please try again."
        finally:
            self.is_submitting = False


# ── Page ────────────────────────────────────────────────────────────────────

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
                "letter_spacing": "0.05em",
            },
        ),
        rx.el.a(
            "Dashboard →",
            href="/dashboard",
            style={
                "font_family": "IBM Plex Mono, monospace",
                "font_size": "0.8125rem",
                "color": "#9ca3af",
                "text_decoration": "none",
                "_hover": {"color": "#E39B42"},
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


def success_panel() -> rx.Component:
    return rx.box(
        rx.el.div(
            rx.el.p(
                "✓",
                style={
                    "font_size": "3rem",
                    "color": "#4ade80",
                    "text_align": "center",
                    "margin_bottom": "0.75rem",
                },
            ),
            rx.el.h2(
                "Complaint Submitted",
                style={
                    "font_family": "Oswald, sans-serif",
                    "font_size": "1.5rem",
                    "font_weight": "700",
                    "color": "#f9fafb",
                    "text_align": "center",
                    "margin_bottom": "0.5rem",
                },
            ),
            rx.el.p(
                f"Reference ID: {SubmitState.submission_id}",
                style={
                    "font_family": "IBM Plex Mono, monospace",
                    "font_size": "0.875rem",
                    "color": "#E39B42",
                    "text_align": "center",
                    "margin_bottom": "1rem",
                },
            ),
            rx.el.p(
                "Your complaint has been received and queued for human review. "
                "Please keep your reference ID for follow-up inquiries.",
                style={
                    "color": "#9ca3af",
                    "font_size": "0.9rem",
                    "text_align": "center",
                    "max_width": "400px",
                    "margin": "0 auto 1.5rem",
                },
            ),
            rx.el.div(
                rx.el.a(
                    "View Dashboard →",
                    href="/dashboard",
                    style={
                        "color": "#E39B42",
                        "font_family": "IBM Plex Mono, monospace",
                        "font_size": "0.875rem",
                        "text_decoration": "underline",
                    },
                ),
                style={"text_align": "center"},
            ),
            style={
                "background": "#1a1b1e",
                "border": "1px solid #374151",
                "border_radius": "0.5rem",
                "padding": "2.5rem 2rem",
                "max_width": "520px",
                "margin": "0 auto",
            },
        ),
        style={
            "padding": "2rem 1rem",
        },
    )


def complaint_form() -> rx.Component:
    return rx.box(
        rx.el.h1(
            "File a Healthcare Complaint",
            style={
                "font_family": "Oswald, sans-serif",
                "font_size": "1.75rem",
                "font_weight": "700",
                "color": "#f9fafb",
                "margin_bottom": "0.5rem",
            },
        ),
        rx.el.p(
            "Your account of events is encrypted and reviewed by a human adjuster. "
            "All submissions are protected under our privacy policy.",
            style={
                "color": "#9ca3af",
                "font_size": "0.9rem",
                "margin_bottom": "2rem",
                "line_height": "1.5",
            },
        ),
        # Error banner
        rx.cond(
            SubmitState.error_message != "",
            rx.el.div(
                rx.el.p(
                    SubmitState.error_message,
                    role="alert",
                    style={"margin": "0", "font_size": "0.9rem"},
                ),
                style={
                    "background": "rgba(220,38,38,0.15)",
                    "border": "1px solid #dc2626",
                    "border_radius": "0.375rem",
                    "padding": "0.75rem 1rem",
                    "color": "#fca5a5",
                    "margin_bottom": "1.25rem",
                },
            ),
            rx.fragment(),
        ),
        rx.el.form(
            labeled_textarea(
                label="What happened?",
                field_id="narrative",
                value=SubmitState.narrative,
                on_change=SubmitState.set_narrative,
                placeholder="Describe the incident in detail. Include dates, names of staff if known, and the impact on your care.",
                required=True,
                min_length=50,
                helper_text="Minimum 50 characters. Your narrative is encrypted before storage.",
            ),
            labeled_input(
                label="Facility or Provider Name",
                field_id="facility_name",
                value=SubmitState.facility_name,
                on_change=SubmitState.set_facility_name,
                placeholder="e.g. Metro General Hospital, Dr. Jane Smith",
                required=True,
            ),
            labeled_input(
                label="Date of Incident",
                field_id="incident_date",
                value=SubmitState.incident_date,
                on_change=SubmitState.set_incident_date,
                input_type="date",
                helper_text="Optional. Helps adjuster timeline verification.",
            ),
            labeled_input(
                label="Contact Email",
                field_id="contact_email",
                value=SubmitState.contact_email,
                on_change=SubmitState.set_contact_email,
                input_type="email",
                placeholder="you@example.com",
                helper_text="Optional. Used only for follow-up if needed.",
            ),
            rx.el.div(
                accessible_button(
                    label="Submit Complaint" if not SubmitState.is_submitting else "Submitting…",
                    on_click=SubmitState.handle_submit,
                    variant="primary",
                    disabled=SubmitState.is_submitting,
                    type="submit",
                ),
                style={"margin_top": "0.5rem"},
            ),
            on_submit=SubmitState.handle_submit,
        ),
        style={
            "background": "#1a1b1e",
            "border": "1px solid #374151",
            "border_radius": "0.5rem",
            "padding": "2rem",
            "max_width": "580px",
            "margin": "0 auto",
        },
    )


@rx.page(route="/", title="File a Complaint — Advocacy Vault")
def submit_complaint_page() -> rx.Component:
    return rx.box(
        nav(),
        # EU AI Act disclosure modal
        rx.cond(
            SubmitState.show_disclosure,
            disclosure_modal(
                on_accept=SubmitState.accept_disclosure,
                on_decline=SubmitState.decline_disclosure,
            ),
            rx.fragment(),
        ),
        rx.box(
            rx.cond(
                SubmitState.success,
                success_panel(),
                complaint_form(),
            ),
            style={
                "padding": "2rem 1rem",
                "min_height": "calc(100vh - 60px)",
            },
        ),
        style={"background": "#0E0F10", "min_height": "100vh"},
    )

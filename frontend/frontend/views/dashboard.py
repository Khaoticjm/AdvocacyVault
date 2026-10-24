"""
Public Dashboard — route: /dashboard
Shows anonymised complaint statistics. No PHI ever surfaced.
"""
import httpx
import reflex as rx

API_BASE = "http://backend:8001/api/v1"


class DashboardState(rx.State):
    complaints: list[dict] = []
    is_loading: bool = True
    error: str = ""
    total: int = 0

    async def load_complaints(self):
        self.is_loading = True
        self.error = ""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(f"{API_BASE}/complaints/")
            if resp.status_code == 200:
                data = resp.json()
                self.complaints = data
                self.total = len(data)
            else:
                self.error = "Unable to load complaints."
        except Exception as exc:
            self.error = f"Network error: {str(exc)}"
        finally:
            self.is_loading = False

    @rx.event
    def on_load(self):
        return DashboardState.load_complaints


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
        rx.box(
            rx.el.a(
                "File a Complaint",
                href="/",
                style={
                    "font_family": "IBM Plex Mono, monospace",
                    "font_size": "0.8125rem",
                    "color": "#9ca3af",
                    "text_decoration": "none",
                    "margin_right": "1.5rem",
                    "_hover": {"color": "#E39B42"},
                },
            ),
            rx.el.a(
                "Adjuster ↗",
                href="/adjuster",
                style={
                    "font_family": "IBM Plex Mono, monospace",
                    "font_size": "0.8125rem",
                    "color": "#9ca3af",
                    "text_decoration": "none",
                    "_hover": {"color": "#E39B42"},
                },
            ),
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


def stat_card(label: str, value) -> rx.Component:
    return rx.box(
        rx.el.p(
            value,
            style={
                "font_family": "Oswald, sans-serif",
                "font_size": "2.25rem",
                "font_weight": "700",
                "color": "#E39B42",
                "margin": "0 0 0.25rem",
            },
        ),
        rx.el.p(
            label,
            style={
                "font_family": "IBM Plex Mono, monospace",
                "font_size": "0.75rem",
                "color": "#9ca3af",
                "text_transform": "uppercase",
                "letter_spacing": "0.1em",
                "margin": "0",
            },
        ),
        style={
            "background": "#1a1b1e",
            "border": "1px solid #374151",
            "border_radius": "0.5rem",
            "padding": "1.25rem 1.5rem",
            "flex": "1",
            "min_width": "140px",
        },
    )


def complaint_row(complaint: dict) -> rx.Component:
    return rx.el.tr(
        rx.el.td(
            rx.el.span(
                complaint.get("id", "")[:8] + "…",
                style={
                    "font_family": "IBM Plex Mono, monospace",
                    "font_size": "0.75rem",
                    "color": "#9ca3af",
                },
            ),
            style={"padding": "0.75rem 1rem"},
        ),
        rx.el.td(
            complaint.get("facility_name", "—"),
            style={
                "padding": "0.75rem 1rem",
                "color": "#e5e7eb",
                "font_size": "0.9rem",
            },
        ),
        rx.el.td(
            complaint.get("incident_date", "—"),
            style={
                "padding": "0.75rem 1rem",
                "color": "#9ca3af",
                "font_family": "IBM Plex Mono, monospace",
                "font_size": "0.8125rem",
            },
        ),
        rx.el.td(
            rx.el.span(
                complaint.get("status", "PENDING"),
                style={
                    "background": "rgba(227,155,66,0.15)",
                    "color": "#E39B42",
                    "font_family": "IBM Plex Mono, monospace",
                    "font_size": "0.7rem",
                    "font_weight": "600",
                    "padding": "0.2rem 0.5rem",
                    "border_radius": "9999px",
                    "text_transform": "uppercase",
                    "letter_spacing": "0.05em",
                },
            ),
            style={"padding": "0.75rem 1rem"},
        ),
        rx.el.td(
            rx.cond(
                complaint.get("human_review_pending", False),
                rx.el.span("⏳ Pending", style={"color": "#fbbf24", "font_size": "0.8rem"}),
                rx.el.span("✓ Reviewed", style={"color": "#4ade80", "font_size": "0.8rem"}),
            ),
            style={"padding": "0.75rem 1rem"},
        ),
        style={
            "border_bottom": "1px solid #1f2937",
            "_hover": {"background": "rgba(255,255,255,0.02)"},
        },
    )


def complaints_table() -> rx.Component:
    return rx.box(
        rx.el.table(
            rx.el.thead(
                rx.el.tr(
                    *[
                        rx.el.th(
                            h,
                            style={
                                "padding": "0.625rem 1rem",
                                "text_align": "left",
                                "font_family": "IBM Plex Mono, monospace",
                                "font_size": "0.7rem",
                                "color": "#6b7280",
                                "text_transform": "uppercase",
                                "letter_spacing": "0.1em",
                                "font_weight": "600",
                            },
                        )
                        for h in ["ID", "Facility", "Date", "Status", "Review"]
                    ]
                ),
                style={"border_bottom": "1px solid #374151"},
            ),
            rx.el.tbody(
                rx.foreach(DashboardState.complaints, complaint_row),
            ),
            style={"width": "100%", "border_collapse": "collapse"},
        ),
        style={
            "background": "#1a1b1e",
            "border": "1px solid #374151",
            "border_radius": "0.5rem",
            "overflow": "hidden",
            "overflow_x": "auto",
        },
    )


@rx.page(route="/dashboard", title="Dashboard — Advocacy Vault", on_load=DashboardState.on_load)
def dashboard_page() -> rx.Component:
    return rx.box(
        nav(),
        rx.box(
            rx.el.h1(
                "Complaint Dashboard",
                style={
                    "font_family": "Oswald, sans-serif",
                    "font_size": "1.75rem",
                    "font_weight": "700",
                    "color": "#f9fafb",
                    "margin_bottom": "0.25rem",
                },
            ),
            rx.el.p(
                "Anonymised complaint log. No personal health information is displayed.",
                style={
                    "color": "#9ca3af",
                    "font_size": "0.875rem",
                    "margin_bottom": "1.5rem",
                },
            ),
            # Stats row
            rx.box(
                stat_card("Total Complaints", DashboardState.total),
                style={
                    "display": "flex",
                    "gap": "1rem",
                    "flex_wrap": "wrap",
                    "margin_bottom": "1.5rem",
                },
            ),
            # Loading / Error / Table
            rx.cond(
                DashboardState.is_loading,
                rx.el.p(
                    "Loading…",
                    style={
                        "color": "#9ca3af",
                        "font_family": "IBM Plex Mono, monospace",
                        "font_size": "0.875rem",
                        "padding": "2rem 0",
                    },
                ),
                rx.cond(
                    DashboardState.error != "",
                    rx.el.div(
                        DashboardState.error,
                        role="alert",
                        style={
                            "background": "rgba(220,38,38,0.15)",
                            "border": "1px solid #dc2626",
                            "border_radius": "0.375rem",
                            "padding": "0.75rem 1rem",
                            "color": "#fca5a5",
                            "font_size": "0.9rem",
                        },
                    ),
                    complaints_table(),
                ),
            ),
            style={
                "max_width": "900px",
                "margin": "0 auto",
                "padding": "2rem 1rem",
            },
        ),
        style={"background": "#0E0F10", "min_height": "100vh"},
    )

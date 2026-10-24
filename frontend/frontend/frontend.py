"""
Advocacy Vault — Reflex frontend entry point.
Three routes: / (submit complaint), /dashboard, /adjuster.
"""
import reflex as rx
from .views.submit_complaint import submit_complaint_page
from .views.dashboard import dashboard_page
from .views.adjuster_workbench import adjuster_page

# Global styles injected into every page
GLOBAL_STYLES = """
@import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;600;700&family=Source+Serif+4:ital,wght@0,400;0,600;1,400&family=IBM+Plex+Mono:wght@400;600&display=swap');

*, *::before, *::after {
    box-sizing: border-box;
}

html, body {
    margin: 0;
    padding: 0;
    background: #0E0F10;
    color: #f9fafb;
    font-family: 'Source Serif 4', Georgia, serif;
    -webkit-font-smoothing: antialiased;
}

:focus-visible {
    outline: 2px solid #E39B42;
    outline-offset: 2px;
}

/* Skip to content link for keyboard users */
.skip-link {
    position: absolute;
    top: -40px;
    left: 0;
    background: #E39B42;
    color: #0E0F10;
    font-weight: 700;
    padding: 0.5rem 1rem;
    z-index: 10000;
    text-decoration: none;
    border-radius: 0 0 4px 0;
    font-family: 'IBM Plex Mono', monospace;
}

.skip-link:focus {
    top: 0;
}

/* Scrollbar */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: #111214;
}
::-webkit-scrollbar-thumb {
    background: #374151;
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
    background: #4b5563;
}
"""

app = rx.App(
    style={
        "background": "#0E0F10",
        "color": "#f9fafb",
        "font_family": "Source Serif 4, Georgia, serif",
    },
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=Oswald:wght@400;600;700&family=Source+Serif+4:ital,wght@0,400;0,600;1,400&family=IBM+Plex+Mono:wght@400;600&display=swap",
    ],
    head_components=[
        rx.el.style(GLOBAL_STYLES),
        rx.el.meta(name="viewport", content="width=device-width, initial-scale=1"),
        rx.el.meta(charset="utf-8"),
        rx.el.meta(
            name="description",
            content="Advocacy Vault — HIPAA-compliant crowdsourced healthcare complaint tracking. AI-assisted, human-reviewed.",
        ),
    ],
)

app.add_page(submit_complaint_page, route="/", title="File a Complaint — Advocacy Vault")
app.add_page(dashboard_page, route="/dashboard", title="Dashboard — Advocacy Vault")
app.add_page(adjuster_page, route="/adjuster", title="Adjuster Workbench — Advocacy Vault")

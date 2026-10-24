"""
EU AI Act Art. 13/14 disclosure modal.
Must be acknowledged before complaint submission is permitted.
"""
import reflex as rx


def disclosure_modal(on_accept, on_decline) -> rx.Component:
    """
    Transparency gate required by EU AI Act Art. 13 (transparency obligations)
    and Art. 14 (human oversight).

    Discloses:
    - That an AI system will analyse submitted content
    - The LLM provider/model identity used for verification
    - That a human adjuster reviews all AI determinations
    - How to request human-only review
    """
    return rx.box(
        # Backdrop
        rx.box(
            style={
                "position": "fixed",
                "inset": "0",
                "background": "rgba(0,0,0,0.75)",
                "z_index": "999",
                "display": "flex",
                "align_items": "center",
                "justify_content": "center",
                "padding": "1rem",
            },
            # Dialog
            rx.box(
                role="dialog",
                aria_modal="true",
                aria_labelledby="modal-title",
                aria_describedby="modal-desc",
                style={
                    "background": "#1a1b1e",
                    "border": "1px solid #374151",
                    "border_radius": "0.5rem",
                    "max_width": "560px",
                    "width": "100%",
                    "padding": "2rem",
                    "max_height": "90vh",
                    "overflow_y": "auto",
                },
                # Icon + Title
                rx.box(
                    rx.el.span(
                        "⚠",
                        aria_hidden="true",
                        style={"font_size": "1.5rem", "margin_right": "0.5rem"},
                    ),
                    rx.el.h2(
                        "AI-Assisted Review Disclosure",
                        id="modal-title",
                        style={
                            "font_family": "Oswald, sans-serif",
                            "font_size": "1.25rem",
                            "font_weight": "700",
                            "color": "#E39B42",
                            "display": "inline",
                        },
                    ),
                    style={"margin_bottom": "1.25rem"},
                ),
                # Body
                rx.el.div(
                    rx.el.p(
                        "Before you submit, please read this disclosure carefully. "
                        "Advocacy Vault uses an AI language model to assist in verifying "
                        "the consistency of submitted evidence. In compliance with the "
                        "EU AI Act (Articles 13 and 14), we are required to inform you of the following:",
                        id="modal-desc",
                        style={
                            "color": "#d1d5db",
                            "font_size": "0.9375rem",
                            "line_height": "1.6",
                            "margin_bottom": "1rem",
                        },
                    ),
                    rx.el.ul(
                        rx.el.li(
                            rx.el.strong("AI System: "),
                            "Your submission will be reviewed by an AI language model "
                            "(model identity logged and available on request).",
                            style={"margin_bottom": "0.5rem"},
                        ),
                        rx.el.li(
                            rx.el.strong("Human Oversight: "),
                            "A human adjuster reviews every AI determination before any "
                            "action is taken. The AI does not make final decisions.",
                            style={"margin_bottom": "0.5rem"},
                        ),
                        rx.el.li(
                            rx.el.strong("Right to Request Human Review: "),
                            "You may request that your submission be reviewed without "
                            "AI involvement by contacting our team directly.",
                            style={"margin_bottom": "0.5rem"},
                        ),
                        rx.el.li(
                            rx.el.strong("Data Protection: "),
                            "Your personal health information is encrypted at rest using "
                            "field-level encryption. Raw IP addresses are never stored.",
                            style={"margin_bottom": "0.5rem"},
                        ),
                        rx.el.li(
                            rx.el.strong("No Automated Decision-Making: "),
                            "No adverse decision affecting your rights is made solely "
                            "through automated processing.",
                        ),
                        style={
                            "color": "#d1d5db",
                            "font_size": "0.9rem",
                            "line_height": "1.6",
                            "padding_left": "1.25rem",
                            "margin_bottom": "1.5rem",
                        },
                    ),
                    rx.el.p(
                        "By clicking \"I Understand, Proceed\" you acknowledge that you "
                        "have read this disclosure and consent to AI-assisted review of "
                        "your submission under the terms described above.",
                        style={
                            "color": "#9ca3af",
                            "font_size": "0.8125rem",
                            "font_style": "italic",
                            "margin_bottom": "1.5rem",
                        },
                    ),
                ),
                # Buttons
                rx.box(
                    rx.el.button(
                        "I Understand, Proceed",
                        on_click=on_accept,
                        style={
                            "background": "#E39B42",
                            "color": "#0E0F10",
                            "font_weight": "700",
                            "font_family": "Oswald, sans-serif",
                            "text_transform": "uppercase",
                            "letter_spacing": "0.05em",
                            "padding": "0.625rem 1.25rem",
                            "border": "none",
                            "border_radius": "0.375rem",
                            "cursor": "pointer",
                            "font_size": "0.9375rem",
                            "_focus": {"outline": "2px solid #E39B42", "outline_offset": "2px"},
                            "_hover": {"background": "#c8862e"},
                        },
                    ),
                    rx.el.button(
                        "Decline",
                        on_click=on_decline,
                        style={
                            "background": "transparent",
                            "color": "#9ca3af",
                            "font_weight": "600",
                            "padding": "0.625rem 1.25rem",
                            "border": "1px solid #374151",
                            "border_radius": "0.375rem",
                            "cursor": "pointer",
                            "font_size": "0.9375rem",
                            "margin_left": "0.75rem",
                            "_focus": {"outline": "2px solid #E39B42", "outline_offset": "2px"},
                            "_hover": {"border_color": "#6b7280", "color": "#d1d5db"},
                        },
                    ),
                    style={"display": "flex", "align_items": "center"},
                ),
            ),
        ),
        style={"display": "contents"},
    )

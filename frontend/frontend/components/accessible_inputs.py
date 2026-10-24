"""
WCAG 2.2 AA accessible form components.
All inputs include visible labels, ARIA attributes, and focus indicators.
"""
import reflex as rx
from typing import Optional


def labeled_textarea(
    label: str,
    field_id: str,
    value: str,
    on_change,
    placeholder: str = "",
    required: bool = False,
    min_length: Optional[int] = None,
    helper_text: Optional[str] = None,
    error_text: Optional[str] = None,
) -> rx.Component:
    """WCAG 2.2 AA compliant textarea with visible label."""
    aria_required = "true" if required else "false"
    label_text = f"{label} *" if required else label

    return rx.box(
        rx.el.label(
            label_text,
            html_for=field_id,
            style={
                "display": "block",
                "font_size": "0.875rem",
                "font_weight": "600",
                "color": "#e5e7eb",
                "margin_bottom": "0.375rem",
                "font_family": "IBM Plex Mono, monospace",
            },
        ),
        rx.cond(
            helper_text is not None,
            rx.el.p(
                helper_text,
                id=f"{field_id}-helper",
                style={
                    "font_size": "0.75rem",
                    "color": "#9ca3af",
                    "margin_bottom": "0.375rem",
                },
            ),
            rx.fragment(),
        ),
        rx.el.textarea(
            id=field_id,
            name=field_id,
            value=value,
            on_change=on_change,
            placeholder=placeholder,
            required=required,
            aria_required=aria_required,
            aria_describedby=f"{field_id}-helper" if helper_text else None,
            min_length=min_length,
            rows=6,
            style={
                "width": "100%",
                "padding": "0.625rem 0.75rem",
                "background": "#1a1b1e",
                "border": "1px solid #374151",
                "border_radius": "0.375rem",
                "color": "#f9fafb",
                "font_size": "0.9375rem",
                "font_family": "Source Serif 4, serif",
                "resize": "vertical",
                "outline_offset": "2px",
                "_focus": {
                    "outline": "2px solid #E39B42",
                    "border_color": "#E39B42",
                },
                "_placeholder": {"color": "#6b7280"},
            },
        ),
        rx.cond(
            error_text is not None,
            rx.el.p(
                error_text,
                role="alert",
                aria_live="polite",
                style={
                    "font_size": "0.75rem",
                    "color": "#f87171",
                    "margin_top": "0.25rem",
                },
            ),
            rx.fragment(),
        ),
        style={"margin_bottom": "1.25rem"},
    )


def labeled_input(
    label: str,
    field_id: str,
    value: str,
    on_change,
    input_type: str = "text",
    placeholder: str = "",
    required: bool = False,
    helper_text: Optional[str] = None,
    error_text: Optional[str] = None,
) -> rx.Component:
    """WCAG 2.2 AA compliant text input with visible label."""
    aria_required = "true" if required else "false"
    label_text = f"{label} *" if required else label

    return rx.box(
        rx.el.label(
            label_text,
            html_for=field_id,
            style={
                "display": "block",
                "font_size": "0.875rem",
                "font_weight": "600",
                "color": "#e5e7eb",
                "margin_bottom": "0.375rem",
                "font_family": "IBM Plex Mono, monospace",
            },
        ),
        rx.cond(
            helper_text is not None,
            rx.el.p(
                helper_text,
                id=f"{field_id}-helper",
                style={
                    "font_size": "0.75rem",
                    "color": "#9ca3af",
                    "margin_bottom": "0.375rem",
                },
            ),
            rx.fragment(),
        ),
        rx.el.input(
            id=field_id,
            name=field_id,
            type=input_type,
            value=value,
            on_change=on_change,
            placeholder=placeholder,
            required=required,
            aria_required=aria_required,
            aria_describedby=f"{field_id}-helper" if helper_text else None,
            style={
                "width": "100%",
                "padding": "0.625rem 0.75rem",
                "background": "#1a1b1e",
                "border": "1px solid #374151",
                "border_radius": "0.375rem",
                "color": "#f9fafb",
                "font_size": "0.9375rem",
                "_focus": {
                    "outline": "2px solid #E39B42",
                    "border_color": "#E39B42",
                },
                "_placeholder": {"color": "#6b7280"},
            },
        ),
        rx.cond(
            error_text is not None,
            rx.el.p(
                error_text,
                role="alert",
                aria_live="polite",
                style={
                    "font_size": "0.75rem",
                    "color": "#f87171",
                    "margin_top": "0.25rem",
                },
            ),
            rx.fragment(),
        ),
        style={"margin_bottom": "1.25rem"},
    )


def accessible_button(
    label: str,
    on_click,
    variant: str = "primary",
    disabled: bool = False,
    aria_label: Optional[str] = None,
    type: str = "button",
) -> rx.Component:
    """WCAG 2.2 AA compliant button."""
    base = {
        "padding": "0.625rem 1.5rem",
        "border_radius": "0.375rem",
        "font_weight": "700",
        "font_size": "0.9375rem",
        "cursor": "pointer" if not disabled else "not-allowed",
        "border": "none",
        "transition": "all 0.15s ease",
        "_focus": {"outline": "2px solid #E39B42", "outline_offset": "2px"},
        "font_family": "Oswald, sans-serif",
        "letter_spacing": "0.05em",
        "text_transform": "uppercase",
    }

    if variant == "primary":
        base.update({
            "background": "#E39B42" if not disabled else "#6b7280",
            "color": "#0E0F10",
            "_hover": {"background": "#c8862e"} if not disabled else {},
        })
    elif variant == "secondary":
        base.update({
            "background": "transparent",
            "color": "#E39B42",
            "border": "1px solid #E39B42",
            "_hover": {"background": "rgba(227,155,66,0.1)"} if not disabled else {},
        })
    elif variant == "danger":
        base.update({
            "background": "#dc2626" if not disabled else "#6b7280",
            "color": "#fff",
            "_hover": {"background": "#b91c1c"} if not disabled else {},
        })

    return rx.el.button(
        label,
        on_click=on_click,
        type=type,
        disabled=disabled,
        aria_label=aria_label or label,
        aria_disabled=str(disabled).lower(),
        style=base,
    )

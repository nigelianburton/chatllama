import reflex as rx

from pepper_reflex.styles import TEXT_MUTED


def settings_item(title: str, body: str) -> rx.Component:
    return rx.box(
        rx.text(title, font_weight="bold"),
        rx.text(body, font_size="0.85rem", color=TEXT_MUTED),
        padding="8px 6px",
    )

import reflex as rx

from pepper_reflex.state import BaseState
from pepper_reflex.styles import (
    NAVBAR_STYLE,
    TEXT_PRIMARY,
    TEXT_MUTED,
    TOGGLE_OFF_BG,
    TOGGLE_OFF_BORDER,
    TOGGLE_OFF_TEXT,
    TOGGLE_ON_BG,
    TOGGLE_ON_BORDER,
    TOGGLE_ON_TEXT,
    TOGGLE_RADIUS,
)


def navbar() -> rx.Component:
    return rx.hstack(
        rx.text(
            rx.cond(
                BaseState.model_name == "None",
                "Model: None",
                rx.text("Model: ", BaseState.model_name),
            ),
            font_weight="bold",
            color=TEXT_PRIMARY,
        ),
        rx.spacer(),
        rx.hstack(
            rx.progress(
                value=BaseState.progress_value,
                width="140px",
                display=rx.cond(BaseState.progress_value > 0, "block", "none"),
            ),
            rx.text(
                BaseState.status_text,
                font_size="0.8rem",
                color=TEXT_MUTED,
            ),
            rx.button(
                "Settings",
                on_click=BaseState.toggle_settings,
                size="2",
                background_color=rx.cond(BaseState.show_settings, TOGGLE_ON_BG, TOGGLE_OFF_BG),
                color=rx.cond(BaseState.show_settings, TOGGLE_ON_TEXT, TOGGLE_OFF_TEXT),
                border=rx.cond(BaseState.show_settings, TOGGLE_ON_BORDER, TOGGLE_OFF_BORDER),
                border_radius=TOGGLE_RADIUS,
            ),
            rx.button(
                "Chat",
                on_click=BaseState.toggle_chat,
                size="2",
                background_color=rx.cond(BaseState.show_chat, TOGGLE_ON_BG, TOGGLE_OFF_BG),
                color=rx.cond(BaseState.show_chat, TOGGLE_ON_TEXT, TOGGLE_OFF_TEXT),
                border=rx.cond(BaseState.show_chat, TOGGLE_ON_BORDER, TOGGLE_OFF_BORDER),
                border_radius=TOGGLE_RADIUS,
            ),
            rx.button(
                "Cards",
                on_click=BaseState.toggle_cards,
                size="2",
                background_color=rx.cond(BaseState.show_cards, TOGGLE_ON_BG, TOGGLE_OFF_BG),
                color=rx.cond(BaseState.show_cards, TOGGLE_ON_TEXT, TOGGLE_OFF_TEXT),
                border=rx.cond(BaseState.show_cards, TOGGLE_ON_BORDER, TOGGLE_OFF_BORDER),
                border_radius=TOGGLE_RADIUS,
            ),
            spacing="2",
            align="center",
        ),
        **NAVBAR_STYLE,
    )

import reflex as rx

from pepper_reflex.state import CardsState
from pepper_reflex.styles import (
    CARD_STYLE,
    CARDS_CONTAINER_STYLE,
    COLUMN_CONTAINER,
    COLUMN_HEADER_STYLE,
    TEXT_PRIMARY,
    TEXT_MUTED,
)


def cards_view() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.text("Cards", font_weight="bold", color=TEXT_PRIMARY),
            **COLUMN_HEADER_STYLE,
        ),
        rx.scroll_area(
            rx.vstack(
                rx.foreach(
                    CardsState.cards,
                    lambda title: rx.card(
                        rx.vstack(
                            rx.text(title, font_weight="bold", color=TEXT_PRIMARY),
                            rx.text("SVG card placeholder", font_size="0.9rem", color=TEXT_MUTED),
                            spacing="2",
                            height="100%",
                        ),
                        **CARD_STYLE,
                    ),
                ),
                spacing="4",
                padding="12px",
                width="100%",
            ),
            type="auto",
            height="100%",
        ),
        spacing="0",
        **COLUMN_CONTAINER,
        **CARDS_CONTAINER_STYLE,
    )

import reflex as rx

from pepper_reflex.components.navbar import navbar
from pepper_reflex.state import BaseState
from pepper_reflex.styles import BACKGROUND, FONT_SANS
from pepper_reflex.views.cards_view import cards_view
from pepper_reflex.views.chat_view import chat_view
from pepper_reflex.views.settings_view import settings_view


def index() -> rx.Component:
    return rx.theme(
        rx.vstack(
            navbar(),
            rx.flex(
                rx.cond(
                    BaseState.show_settings,
                    rx.box(settings_view(), flex="1", height="100%"),
                    rx.fragment(),
                ),
                rx.cond(
                    BaseState.show_chat,
                    rx.box(chat_view(), flex="1", height="100%"),
                    rx.fragment(),
                ),
                rx.cond(
                    BaseState.show_cards,
                    rx.box(cards_view(), flex="1", height="100%"),
                    rx.fragment(),
                ),
                align_items="stretch",
                gap="8px",
                padding="8px",
                width="100%",
                height="100vh",
                max_height="100vh",
                overflow="hidden",
            ),
            height="100vh",
            width="100%",
            spacing="0",
            background_color=BACKGROUND,
        ),
        appearance="dark",
    )


app = rx.App(style={"font_family": FONT_SANS})
app.add_page(index, route="/")

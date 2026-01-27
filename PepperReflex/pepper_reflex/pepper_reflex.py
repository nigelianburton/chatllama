import reflex as rx

from pepper_reflex.components.navbar import navbar
from pepper_reflex.state import BaseState
from pepper_reflex.styles import BACKGROUND, FONT_SANS
from pepper_reflex.views.cards_view import cards_view
from pepper_reflex.views.chat_view import chat_view
from pepper_reflex.views.settings_view import settings_view


def index() -> rx.Component:
    return rx.theme(
        rx.flex(
            rx.el.style(
                """
                textarea.rt-TextAreaInput,
                .rt-TextAreaRoot textarea,
                textarea {
                    color: white !important;
                    -webkit-text-fill-color: #ffffff !important;
                    background-color: #25262b !important;
                }
                .rt-TextAreaInput:focus, textarea:focus {
                    outline: 1px solid #4dabf7 !important;
                }
                textarea::placeholder {
                    color: #adb5bd !important;
                }
                """
            ),
            navbar(),
            rx.hstack(
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
                height="100%",
                width="100%",
                align_items="stretch",
                overflow="hidden",
            ),
            direction="column",
            height="100vh",
            max_height="100vh",
            overflow="hidden",
            width="100%",
            background_color=BACKGROUND,
        ),
        appearance="dark",
    )


app = rx.App(style={"font_family": FONT_SANS})
app.add_page(index, route="/")

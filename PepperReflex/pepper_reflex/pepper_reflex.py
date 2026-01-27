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
                .rt-TextAreaInput, textarea {
                    color: white !important;
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
            rx.el.div(
                rx.cond(
                    BaseState.show_settings,
                    rx.el.div(
                        settings_view(),
                        style={
                            "resize": "horizontal",
                            "overflow": "auto",
                            "minWidth": "240px",
                            "maxWidth": "45%",
                            "height": "100%",
                        },
                    ),
                    rx.fragment(),
                ),
                rx.cond(
                    BaseState.show_chat,
                    rx.el.div(
                        chat_view(),
                        style={
                            "minWidth": "320px",
                            "height": "100%",
                        },
                    ),
                    rx.fragment(),
                ),
                rx.cond(
                    BaseState.show_cards,
                    rx.el.div(
                        cards_view(),
                        style={
                            "resize": "horizontal",
                            "overflow": "auto",
                            "minWidth": "240px",
                            "maxWidth": "45%",
                            "height": "100%",
                        },
                    ),
                    rx.fragment(),
                ),
                style={
                    "display": "grid",
                    "gridTemplateColumns": BaseState.grid_template_columns,
                    "height": "100%",
                    "width": "100%",
                    "overflow": "hidden",
                },
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

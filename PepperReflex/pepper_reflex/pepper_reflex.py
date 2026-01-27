import reflex as rx
import reflex_resizable_panels as resizable

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
                .rt-TextAreaInput, .rt-TextAreaRoot textarea, textarea {
                    color: #ffffff !important;
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
            resizable.PanelGroup.create(
                resizable.Panel.create(
                    rx.cond(BaseState.show_settings, settings_view(), rx.fragment()),
                    id="settings",
                    order=1,
                    min_size=rx.cond(BaseState.show_settings, 15, 0),
                    default_size=25,
                ),
                resizable.PanelResizeHandle.create(width="4px", background_color="#373a40"),
                resizable.Panel.create(
                    resizable.PanelGroup.create(
                        resizable.Panel.create(
                            rx.cond(BaseState.show_chat, chat_view(), rx.fragment()),
                            id="chat",
                            order=1,
                            min_size=rx.cond(BaseState.show_chat, 20, 0),
                            default_size=50,
                        ),
                        resizable.PanelResizeHandle.create(width="4px", background_color="#373a40"),
                        resizable.Panel.create(
                            rx.cond(BaseState.show_cards, cards_view(), rx.fragment()),
                            id="cards",
                            order=2,
                            min_size=rx.cond(BaseState.show_cards, 15, 0),
                            default_size=25,
                        ),
                        direction="horizontal",
                    ),
                    id="main-content",
                    order=2,
                ),
                direction="horizontal",
                height="100%",
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
app.add_page(index, route="/", on_load=BaseState.poll_control_service)

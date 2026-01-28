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
            rx.window_event_listener(on_before_unload=BaseState.on_before_unload),
            navbar(),
            resizable.PanelGroup.create(
                resizable.Panel.create(
                    rx.cond(BaseState.show_settings, settings_view(), rx.fragment()),
                    id="settings",
                    order=1,
                    min_size=rx.cond(BaseState.show_settings, 15, 0),
                    default_size=rx.cond(
                        BaseState.show_settings,
                        rx.cond(
                            BaseState.show_chat & BaseState.show_cards,
                            33,
                            rx.cond(BaseState.show_chat | BaseState.show_cards, 50, 100),
                        ),
                        0,
                    ),
                    max_size=rx.cond(BaseState.show_settings, 100, 0),
                    style={"display": rx.cond(BaseState.show_settings, "flex", "none")},
                ),
                rx.cond(
                    BaseState.show_settings & (BaseState.show_chat | BaseState.show_cards),
                    resizable.PanelResizeHandle.create(width="4px", background_color="#373a40"),
                    rx.fragment(),
                ),
                resizable.Panel.create(
                    resizable.PanelGroup.create(
                        resizable.Panel.create(
                            rx.cond(BaseState.show_chat, chat_view(), rx.fragment()),
                            id="chat",
                            order=1,
                            min_size=rx.cond(BaseState.show_chat, 20, 0),
                            default_size=rx.cond(
                                BaseState.show_chat,
                                rx.cond(BaseState.show_cards, 50, 100),
                                0,
                            ),
                            max_size=rx.cond(BaseState.show_chat, 100, 0),
                            style={"display": rx.cond(BaseState.show_chat, "flex", "none")},
                        ),
                        rx.cond(
                            BaseState.show_chat & BaseState.show_cards,
                            resizable.PanelResizeHandle.create(width="4px", background_color="#373a40"),
                            rx.fragment(),
                        ),
                        resizable.Panel.create(
                            rx.cond(BaseState.show_cards, cards_view(), rx.fragment()),
                            id="cards",
                            order=2,
                            min_size=rx.cond(BaseState.show_cards, 15, 0),
                            default_size=rx.cond(
                                BaseState.show_cards,
                                rx.cond(BaseState.show_chat, 50, 100),
                                0,
                            ),
                            max_size=rx.cond(BaseState.show_cards, 100, 0),
                            style={"display": rx.cond(BaseState.show_cards, "flex", "none")},
                        ),
                        direction="horizontal",
                        key=rx.cond(
                            BaseState.show_chat,
                            rx.cond(BaseState.show_cards, "layout-inner-11", "layout-inner-10"),
                            rx.cond(BaseState.show_cards, "layout-inner-01", "layout-inner-00"),
                        ),
                    ),
                    id="main-content",
                    order=2,
                ),
                direction="horizontal",
                height="100%",
                key=rx.cond(
                    BaseState.show_settings,
                    rx.cond(BaseState.show_chat, rx.cond(BaseState.show_cards, "layout-111", "layout-110"), "layout-100"),
                    rx.cond(BaseState.show_chat, rx.cond(BaseState.show_cards, "layout-011", "layout-010"), "layout-001"),
                ),
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
app.add_page(index, route="/", on_load=BaseState.init_control_service)

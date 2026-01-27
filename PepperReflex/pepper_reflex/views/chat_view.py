import reflex as rx

from pepper_reflex.components.chat_bubble import chat_bubble
from pepper_reflex.state import ChatState
from pepper_reflex.styles import (
    CHAT_INPUT_ROW,
    CHAT_SCROLL_STYLE,
    CHAT_TEXTAREA_STYLE,
    COLUMN_CONTAINER,
    COLUMN_HEADER_STYLE,
    SEND_BUTTON_STYLE,
    TEXT_PRIMARY,
)


def chat_view() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.text("Chat", font_weight="bold", color=TEXT_PRIMARY),
            **COLUMN_HEADER_STYLE,
        ),
        rx.box(
            rx.vstack(
                rx.foreach(
                    ChatState.messages,
                    lambda msg: chat_bubble(msg["role"], msg["text"]),
                ),
                rx.hstack(
                    rx.text_area(
                        placeholder="Type a message...",
                        value=ChatState.input_text,
                        on_change=ChatState.set_input_text,
                        color="white",
                        background_color="#25262b",
                        style={
                            "color": "white !important",
                            "background_color": "#25262b !important",
                        },
                        **CHAT_TEXTAREA_STYLE,
                    ),
                    rx.button(
                        "Send",
                        on_click=ChatState.send_message,
                        size="2",
                        **SEND_BUTTON_STYLE,
                    ),
                    **CHAT_INPUT_ROW,
                ),
                spacing="2",
                width="100%",
                height="100%",
                padding="8px",
                align_items="stretch",
            ),
            overflow_y="auto",
            flex="1",
            width="100%",
            **CHAT_SCROLL_STYLE,
        ),
        spacing="0",
        height="100%",
        flex="1",
    )

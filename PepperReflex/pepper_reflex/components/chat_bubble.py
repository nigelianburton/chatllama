import reflex as rx

from pepper_reflex.styles import (
    ASSISTANT_BUBBLE,
    FONT_MONO,
    FONT_SANS,
    MCP_BORDER_COLOR,
    MCP_BUBBLE,
    SECTION_BORDER,
    TEXT_PRIMARY,
    USER_BUBBLE,
)


def chat_bubble(role: rx.Var, text: rx.Var) -> rx.Component:
    is_user = role == "user"
    is_mcp = role == "mcp_request"
    return rx.hstack(
        rx.box(
            rx.text(
                text,
                font_size="0.9rem",
                font_family=rx.cond(is_mcp, FONT_MONO, FONT_SANS),
                color=TEXT_PRIMARY,
            ),
            padding="8px 10px",
            background_color=rx.cond(
                is_mcp,
                MCP_BUBBLE,
                rx.cond(is_user, USER_BUBBLE, ASSISTANT_BUBBLE),
            ),
            border=rx.cond(is_mcp, f"1px solid {MCP_BORDER_COLOR}", f"1px solid {SECTION_BORDER}"),
            border_radius=rx.cond(is_mcp, "4px", "10px"),
            max_width="80%",
        ),
        justify=rx.cond(is_user, "flex-end", "flex-start"),
        width="100%",
    )

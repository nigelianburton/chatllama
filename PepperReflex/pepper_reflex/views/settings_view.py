import reflex as rx

from pepper_reflex.state import SettingsState
from pepper_reflex.styles import (
    ACCORDION_ROOT_STYLE,
    ACCORDION_TRIGGER_STYLE,
    ACCORDION_ITEM_STYLE,
    COLUMN_CONTAINER,
    COLUMN_HEADER_STYLE,
    MODEL_READY_COLOR,
    SETTINGS_PANEL_STYLE,
    TEXT_MUTED,
)


def settings_view() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.text("Settings", font_weight="bold"),
            **COLUMN_HEADER_STYLE,
        ),
        rx.box(
            rx.box(
                rx.accordion.root(
                    rx.accordion.item(
                        rx.accordion.header(
                            rx.accordion.trigger(
                                "Models",
                                **ACCORDION_TRIGGER_STYLE,
                            ),
                        ),
                        rx.accordion.content(
                            rx.vstack(
                                rx.text(
                                    "Model: ",
                                    SettingsState.selected_model,
                                    color=rx.cond(
                                        SettingsState.model_ready,
                                        MODEL_READY_COLOR,
                                        TEXT_MUTED,
                                    ),
                                    font_weight="bold",
                                ),
                                rx.hstack(
                                    rx.select(
                                        SettingsState.model_options,
                                        value=SettingsState.selected_model,
                                        on_change=SettingsState.set_selected_model,
                                        width="100%",
                                    ),
                                    rx.button("Load", on_click=SettingsState.load_model),
                                    spacing="2",
                                    width="100%",
                                ),
                                spacing="3",
                                width="100%",
                            )
                        ),
                        value="models",
                        **ACCORDION_ITEM_STYLE,
                    ),
                    rx.accordion.item(
                        rx.accordion.header(
                            rx.accordion.trigger(
                                "MCP Tools",
                                **ACCORDION_TRIGGER_STYLE,
                            ),
                        ),
                        rx.accordion.content(
                            rx.vstack(
                                rx.foreach(
                                    SettingsState.mcp_items,
                                    lambda item: rx.vstack(
                                        rx.hstack(
                                            rx.button(
                                                rx.cond(item["enabled"], "✓", "✗"),
                                                on_click=SettingsState.toggle_mcp(item["name"]),
                                                size="1",
                                            ),
                                            rx.text(
                                                item["name"],
                                                font_weight="bold",
                                            ),
                                            rx.spacer(),
                                            rx.button("✕", on_click=SettingsState.delete_mcp),
                                            spacing="2",
                                            width="100%",
                                        ),
                                        rx.cond(
                                            item["transport"] == "http",
                                            rx.hstack(
                                                rx.input(
                                                    value=item["url"],
                                                    placeholder="URL",
                                                    width="70%",
                                                ),
                                                rx.input(
                                                    value=item["port"],
                                                    placeholder="PORT",
                                                    width="30%",
                                                ),
                                                spacing="2",
                                                width="100%",
                                            ),
                                            rx.fragment(),
                                        ),
                                        spacing="2",
                                        width="100%",
                                    ),
                                ),
                                spacing="3",
                                width="100%",
                            )
                        ),
                        value="mcp-tools",
                        **ACCORDION_ITEM_STYLE,
                    ),
                    rx.accordion.item(
                        rx.accordion.header(
                            rx.accordion.trigger(
                                "Built-in MCPs",
                                **ACCORDION_TRIGGER_STYLE,
                            ),
                        ),
                        rx.accordion.content(
                            rx.vstack(
                                rx.foreach(
                                    SettingsState.built_in_mcps,
                                    lambda item: rx.vstack(
                                        rx.hstack(
                                            rx.text(
                                                rx.cond(item["enabled"], "✓", "✗"),
                                                color=rx.cond(
                                                    item["enabled"],
                                                    "#1c7c1c",
                                                    "#d9480f",
                                                ),
                                                font_weight="bold",
                                            ),
                                            rx.text(item["name"], font_weight="bold"),
                                            spacing="2",
                                            width="100%",
                                        ),
                                        rx.hstack(
                                            rx.foreach(
                                                item["methods"],
                                                lambda method: rx.box(
                                                    rx.text(method, font_size="0.8rem"),
                                                    padding="2px 6px",
                                                    border="1px solid #999",
                                                    background_color="#1f2329",
                                                    border_radius="4px",
                                                ),
                                            ),
                                            spacing="2",
                                            wrap="wrap",
                                        ),
                                        spacing="2",
                                        width="100%",
                                    ),
                                ),
                                spacing="3",
                                width="100%",
                            )
                        ),
                        value="built-in-mcps",
                        **ACCORDION_ITEM_STYLE,
                    ),
                    rx.accordion.item(
                        rx.accordion.header(
                            rx.accordion.trigger(
                                "Autorun",
                                **ACCORDION_TRIGGER_STYLE,
                            ),
                        ),
                        rx.accordion.content(
                            rx.text(
                                "Run scripted prompts and capture screenshots.",
                                color=TEXT_MUTED,
                            )
                        ),
                        value="autorun",
                        **ACCORDION_ITEM_STYLE,
                    ),
                    rx.accordion.item(
                        rx.accordion.header(
                            rx.accordion.trigger(
                                "Logging",
                                **ACCORDION_TRIGGER_STYLE,
                            ),
                        ),
                        rx.accordion.content(
                            rx.text(
                                "Session logs, interaction JSON, and diagnostics.",
                                color=TEXT_MUTED,
                            )
                        ),
                        value="logging",
                        **ACCORDION_ITEM_STYLE,
                    ),
                    type="multiple",
                    collapsible=True,
                    variant="soft",
                    **ACCORDION_ROOT_STYLE,
                ),
                **SETTINGS_PANEL_STYLE,
            ),
            overflow_y="auto",
            flex="1",
            width="100%",
        ),
        spacing="0",
        height="100%",
        flex="1",
    )

import reflex as rx

from pepper_reflex.components.settings_item import settings_item
from pepper_reflex.state import SettingsState
from pepper_reflex.styles import (
    ACCORDION_TRIGGER_STYLE,
    ACCORDION_ITEM_STYLE,
    COLUMN_CONTAINER,
    COLUMN_HEADER_STYLE,
    SETTINGS_PANEL_STYLE,
)


def settings_view() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.text("Settings", font_weight="bold"),
            **COLUMN_HEADER_STYLE,
        ),
        rx.box(
            rx.accordion.root(
                rx.foreach(
                    SettingsState.sections,
                    lambda section: rx.accordion.item(
                        rx.accordion.header(
                            rx.accordion.trigger(
                                section["title"],
                                **ACCORDION_TRIGGER_STYLE,
                            ),
                        ),
                        rx.accordion.content(
                            settings_item(section["title"], section["body"])
                        ),
                        value=section["title"].lower().replace(" ", "-"),
                        **ACCORDION_ITEM_STYLE,
                    ),
                ),
                type="multiple",
                collapsible=True,
                variant="soft",
                width="100%",
            ),
            **SETTINGS_PANEL_STYLE,
        ),
        spacing="0",
        **COLUMN_CONTAINER,
    )

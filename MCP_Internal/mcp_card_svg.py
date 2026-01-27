from __future__ import annotations

from typing import Any, Callable

from MCP_Internal import card_svg
from MCP_Internal.card_svg_handler import get_instructions as get_svg_instructions


def register_tools(
    server: Any,
    ui_invoke: Callable[[Callable[[], object]], object],
    ui_create_card: Callable[[str, bool], card_svg.SVGCard],
    ui_delete_card: Callable[[card_svg.SVGCard], None],
    cards: dict[str, card_svg.SVGCard],
    name_prefix: str | None = None,
) -> None:
    card_svg.register_tools(
        server=server,
        ui_invoke=ui_invoke,
        ui_create_card=ui_create_card,
        ui_delete_card=ui_delete_card,
        cards=cards,
        name_prefix=name_prefix,
    )


def get_instructions(name_prefix: str | None = None) -> str:
    return get_svg_instructions(name_prefix=name_prefix)


MCP_TOOL_NAMES = ["CreateCard", "DrawCard", "DeleteCard"]


def get_tool_names() -> list[str]:
    return list(MCP_TOOL_NAMES)

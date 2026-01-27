from __future__ import annotations

from typing import Any, Callable

from MCP_Internal.card_svg import SVGCard
from MCP_Internal.card_textviewer_handler import (
    build_svg_from_text,
    get_instructions,
    validate_text,
)


def register_tools(
    server: Any,
    ui_invoke: Callable[[Callable[[], object]], object],
    ui_create_card: Callable[[str, bool], SVGCard],
    ui_delete_card: Callable[[SVGCard], None],
    cards: dict[str, SVGCard],
    name_prefix: str | None = None,
) -> None:
    instructions = get_instructions(name_prefix)

    def _tool_name(base: str) -> str:
        return f"{name_prefix}.{base}" if name_prefix else base

    def _error(message: str) -> dict[str, str]:
        return {"status": "error", "message": message, "hint": instructions}

    @server.tool(name=_tool_name("CreateCard"))
    def CreateCard(isPortrait: bool = True) -> str | dict:
        """Create a text viewer card and return its GUID."""
        import uuid

        guid = str(uuid.uuid4())

        def _create() -> SVGCard:
            return ui_create_card(guid, isPortrait)

        card = ui_invoke(_create)
        if not isinstance(card, SVGCard):
            return _error("UI did not return SVGCard")
        cards[guid] = card
        return {"status": "ok", "guid": guid}

    @server.tool(name=_tool_name("DeleteCard"))
    def DeleteCard(GUID: str) -> dict:
        """Delete a text viewer card by GUID."""
        card = cards.get(GUID)
        if not card:
            return _error("Card not found. Use CreateCard first to obtain a GUID.")

        def _delete() -> None:
            ui_delete_card(card)

        ui_invoke(_delete)
        cards.pop(GUID, None)
        return {"status": "ok", "guid": GUID}

    @server.tool(name=_tool_name("DrawCard"))
    def DrawCard(GUID: str, text: str) -> dict:
        """Render multiline text into an existing card."""
        card = cards.get(GUID)
        if not card:
            return _error("Card not found. Use CreateCard first to obtain a GUID.")

        text_error = validate_text(text)
        if text_error:
            return _error(text_error)

        svg = build_svg_from_text(text, card.is_portrait)

        def _draw() -> None:
            card.load_svg_content(svg)

        ui_invoke(_draw)
        return {"status": "ok", "guid": GUID}


__all__ = ["register_tools", "get_instructions"]

MCP_TOOL_NAMES = ["CreateCard", "DrawCard", "DeleteCard"]


def get_tool_names() -> list[str]:
    return list(MCP_TOOL_NAMES)

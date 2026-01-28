from __future__ import annotations

import uuid
from typing import Any, Callable, TypeVar

from PyQt6 import QtWidgets


TCard = TypeVar("TCard", bound=QtWidgets.QWidget)


def register_create_delete_tools(
    *,
    server: Any,
    name_prefix: str | None,
    ui_invoke: Callable[[Callable[[], object]], object],
    ui_create_card: Callable[..., TCard],
    ui_delete_card: Callable[[TCard], None],
    cards: dict[str, TCard],
    card_cls: type[TCard],
    error_factory: Callable[[str], dict[str, str]],
    create_card: Callable[[str, bool], TCard],
    card_label: str = "card",
) -> None:
    def _tool_name(base: str) -> str:
        return f"{name_prefix}.{base}" if name_prefix else base

    @server.tool(name=_tool_name("CreateCard"))
    def CreateCard(isPortrait: bool = True) -> str | dict:
        """Create a card and return its GUID."""
        guid = str(uuid.uuid4())

        def _create() -> TCard:
            return create_card(guid, isPortrait)

        card = ui_invoke(_create)
        if not isinstance(card, card_cls):
            return error_factory(f"UI did not return {card_cls.__name__}")
        cards[guid] = card
        return {"status": "ok", "guid": guid}

    @server.tool(name=_tool_name("DeleteCard"))
    def DeleteCard(GUID: str) -> dict:
        """Delete a card by GUID."""
        card = cards.get(GUID)
        if not card:
            return error_factory(f"{card_label.title()} not found. Use CreateCard first to obtain a GUID.")

        def _delete() -> None:
            ui_delete_card(card)

        ui_invoke(_delete)
        cards.pop(GUID, None)
        return {"status": "ok", "guid": GUID}

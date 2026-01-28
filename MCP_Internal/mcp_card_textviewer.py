from __future__ import annotations

import html
import textwrap
from typing import Any, Callable

from MCP_Internal.mcp_card_svg import SVGCard
from MCP_Internal.mcp_card_helper import register_create_delete_tools


INTERNAL_MCP_INSTRUCTIONS_TEMPLATE = (
    "## Text Card Rules\n"
    "1. **Workflow**: {create_tool} (returns GUID) -> {draw_tool} (uses GUID).\n"
    "2. **Strict Constraint**: Use {draw_tool} ONLY for plain, human-readable multiline text. PROHIBITED for SVG, HTML, or code.\n"
    "3. **Formatting**: Text is rendered in a standard font; no custom styling or markup is supported.\n"
    "4. **Assistant Output**: Confirm tool success briefly. Do not repeat the text in chat."
)


def get_instructions(name_prefix: str | None = None) -> str:
    prefix = f"{name_prefix}." if name_prefix else ""
    return INTERNAL_MCP_INSTRUCTIONS_TEMPLATE.format(
        create_tool=f"{prefix}CreateCard",
        draw_tool=f"{prefix}RenderText",
        delete_tool=f"{prefix}DeleteCard",
    )


def validate_text(text: str) -> str | None:
    if not text or not text.strip():
        return "Text content must not be empty."
    return None


def build_svg_from_text(text: str, is_portrait: bool) -> str:
    width, height = (480, 640) if is_portrait else (640, 480)
    font_size = 20
    padding = 24
    max_chars = max(int((width - (padding * 2)) / (font_size * 0.55)), 10)
    lines = _wrap_text(text, max_chars)
    line_height = int(font_size * 1.4)
    max_lines = max(int((height - (padding * 2)) / line_height), 1)
    lines = lines[:max_lines]
    start_x = padding
    start_y = padding + font_size

    text_elements = []
    for index, line in enumerate(lines):
        safe_line = html.escape(line)
        y = start_y + index * line_height
        text_elements.append(
            f"<text x=\"{start_x}\" y=\"{y}\" font-family=\"Arial\" font-size=\"{font_size}\" fill=\"#1f1f1f\">{safe_line}</text>"
        )

    text_block = "\n  ".join(text_elements) if text_elements else ""

    return (
        f"<svg width=\"{width}\" height=\"{height}\" viewBox=\"0 0 {width} {height}\" xmlns=\"http://www.w3.org/2000/svg\">\n"
        f"  <rect width=\"{width}\" height=\"{height}\" fill=\"#ffffff\" stroke=\"#d0d0d0\"/>\n"
        f"  {text_block}\n"
        f"</svg>"
    )


def _normalize_lines(text: str) -> list[str]:
    return [line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]


def _wrap_text(text: str, max_chars: int) -> list[str]:
    normalized = _normalize_lines(text)
    wrapped: list[str] = []
    for line in normalized:
        if not line.strip():
            wrapped.append("")
            continue
        wrapped.extend(
            textwrap.wrap(
                line,
                width=max_chars,
                break_long_words=True,
                break_on_hyphens=False,
            )
        )
    return wrapped


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

    register_create_delete_tools(
        server=server,
        name_prefix=name_prefix,
        ui_invoke=ui_invoke,
        ui_create_card=ui_create_card,
        ui_delete_card=ui_delete_card,
        cards=cards,
        card_cls=SVGCard,
        error_factory=_error,
        create_card=lambda guid, is_portrait: ui_create_card(guid, is_portrait),
        card_label="card",
    )

    @server.tool(name=_tool_name("RenderText"))
    def RenderText(GUID: str, text_content: str) -> dict:
        """Render multiline text into an existing card."""
        card = cards.get(GUID)
        if not card:
            return _error("Card not found. Use CreateCard first to obtain a GUID.")

        text_error = validate_text(text_content)
        if text_error:
            return _error(text_error)

        svg = build_svg_from_text(text_content, card.is_portrait)

        def _draw() -> None:
            card.load_svg_content(svg)

        ui_invoke(_draw)
        return {"status": "ok", "guid": GUID}


__all__ = ["register_tools", "get_instructions"]

MCP_TOOL_NAMES = ["CreateCard", "RenderText", "DeleteCard"]


def get_tool_names() -> list[str]:
    return list(MCP_TOOL_NAMES)

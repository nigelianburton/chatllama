from __future__ import annotations

import html


INTERNAL_MCP_INSTRUCTIONS_TEMPLATE = (
    "You can only use these tools: {create_tool}, {draw_tool}, {delete_tool}. "
    "You MUST call {create_tool} first to get a guid; never invent or guess guids. "
    "{create_tool} returns a response with a guid field. "
    "Then pass that exact guid to {draw_tool}. "
    "{draw_tool} renders multiline text in the card. "
    "Never output SVG in assistant messages; only provide text inside the {draw_tool} tool call arguments. "
    "After {draw_tool} succeeds, reply with a brief confirmation and do not call {draw_tool} again unless the user requests changes."
)


def get_instructions(name_prefix: str | None = None) -> str:
    prefix = f"{name_prefix}." if name_prefix else ""
    return INTERNAL_MCP_INSTRUCTIONS_TEMPLATE.format(
        create_tool=f"{prefix}CreateCard",
        draw_tool=f"{prefix}DrawCard",
        delete_tool=f"{prefix}DeleteCard",
    )


def validate_text(text: str) -> str | None:
    if not text or not text.strip():
        return "Text content must not be empty."
    return None


def build_svg_from_text(text: str, is_portrait: bool) -> str:
    width, height = (480, 640) if is_portrait else (640, 480)
    lines = _normalize_lines(text)
    font_size = 18
    line_height = int(font_size * 1.4)
    start_x = 24
    start_y = 40

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

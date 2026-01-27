from __future__ import annotations

import base64
import re
from pathlib import Path


RESOURCES_DIR = Path(__file__).resolve().parents[1] / "resources"
RESOURCE_SCHEME = "resource:"

INTERNAL_MCP_INSTRUCTIONS_TEMPLATE = (
    "You can only use these tools: {create_tool}, {draw_tool}, {delete_tool}. "
    "You MUST call {create_tool} first to get a guid; never invent or guess guids. "
    "{create_tool} returns a response with a guid field. "
    "Then pass that exact guid to {draw_tool}. "
    "{draw_tool} requires full SVG markup with a <svg> root sized 480x640 (portrait) or 640x480 (landscape). "
    "Never output SVG in assistant messages; only provide svg_instructions inside the {draw_tool} tool call arguments. "
    "After {draw_tool} succeeds, reply with a brief confirmation and do not call {draw_tool} again unless the user requests changes. "
    "For images, use href values like resource:pic1-portrait.jpg or resource:pic2-landscape.jpg (from the resources folder). "
    "Do not embed base64 images in prompts. Do not call any other tools."
)


def get_instructions(name_prefix: str | None = None) -> str:
    prefix = f"{name_prefix}." if name_prefix else ""
    return INTERNAL_MCP_INSTRUCTIONS_TEMPLATE.format(
        create_tool=f"{prefix}CreateCard",
        draw_tool=f"{prefix}DrawCard",
        delete_tool=f"{prefix}DeleteCard",
    )


def validate_svg(svg: str) -> str | None:
    if not svg:
        return "SVG must be full <svg> markup. Include a <svg> root element and closing </svg>."
    trimmed = svg.strip()
    if not trimmed.startswith("<svg") or not trimmed.endswith("</svg>"):
        return "svg_instructions must be ONLY a single <svg>...</svg> document with no extra text."
    if "<svg" not in trimmed or "</svg>" not in trimmed:
        return "SVG must be full <svg> markup. Include a <svg> root element and closing </svg>."
    return None


def replace_resource_refs(svg: str) -> tuple[str, list[str]]:
    missing: list[str] = []

    def _resource_to_data_uri(resource_value: str) -> str | None:
        name = resource_value[len(RESOURCE_SCHEME) :].lstrip("/")
        name = Path(name).name
        if not name:
            return None
        path = RESOURCES_DIR / name
        if not path.exists():
            return None
        data = path.read_bytes()
        ext = path.suffix.lower()
        mime = "image/jpeg" if ext in {".jpg", ".jpeg"} else "image/png"
        b64 = base64.b64encode(data).decode("ascii")
        return f"data:{mime};base64,{b64}"

    def _replace(match: re.Match[str]) -> str:
        attr = match.group("attr")
        quote = match.group("quote")
        value = match.group("value")
        if not value.startswith(RESOURCE_SCHEME):
            return match.group(0)
        data_uri = _resource_to_data_uri(value)
        if data_uri is None:
            missing.append(value)
            return match.group(0)
        return f"{attr}={quote}{data_uri}{quote}"

    pattern = r"(?P<attr>xlink:href|href)=(?P<quote>['\"])(?P<value>[^'\"]+)(?P=quote)"
    updated = re.sub(pattern, _replace, svg)
    return updated, missing

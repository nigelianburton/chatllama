from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Any, Callable

from PyQt6 import QtCore, QtGui, QtWidgets, QtSvgWidgets

from Engine.logger import get_logger
from MCP_Internal.mcp_card_helper import register_create_delete_tools


RESOURCES_DIR = Path(__file__).resolve().parents[1] / "resources"
RESOURCE_SCHEME = "resource:"

INTERNAL_MCP_INSTRUCTIONS_TEMPLATE = (
    "## SVG Card Rules\n"
    "1. **Workflow**: {create_tool} (returns GUID) -> {draw_tool} (uses GUID).\n"
    "2. **Strict Constraint**: Use {draw_tool} ONLY for complex graphics/layouts. PROHIBITED for plain text.\n"
    "3. **Format**: {draw_tool} requires 480x640 (portrait) or 640x480 (landscape) <svg> markup.\n"
    "4. **Assets**: Use 'resource:filename' for images. No Base64.\n"
    "5. **Assistant Output**: Confirm tool success briefly. Never output raw SVG in chat."
)


def get_instructions(name_prefix: str | None = None) -> str:
    prefix = f"{name_prefix}." if name_prefix else ""
    return INTERNAL_MCP_INSTRUCTIONS_TEMPLATE.format(
        create_tool=f"{prefix}CreateCard",
        draw_tool=f"{prefix}RenderSVG",
        delete_tool=f"{prefix}DeleteCard",
    )


def validate_svg(svg: str) -> str | None:
    if not svg:
        return "SVG must be full <svg> markup. Include a <svg> root element and closing </svg>."
    trimmed = svg.strip()
    if not trimmed.startswith("<svg") or not trimmed.endswith("</svg>"):
        return "svg_markup must be ONLY a single <svg>...</svg> document with no extra text."
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


class SVGCard(QtWidgets.QFrame):
    def __init__(self, guid: str, is_portrait: bool) -> None:
        super().__init__()
        self._logger = get_logger(self)
        self.guid = guid
        self.is_portrait = is_portrait

        width, height = (480, 640) if is_portrait else (640, 480)
        self._aspect_ratio = height / width
        self._parent_filter_installed = False
        self.setSizePolicy(
            QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        )
        self.setStyleSheet("background-color: white; border: 1px solid #999;")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._view = QtSvgWidgets.QSvgWidget(self)
        self._view.setSizePolicy(
            QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        )
        layout.addWidget(self._view)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._sync_height_to_width()

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        self._install_parent_filter()
        self._sync_height_to_width()

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.Type.Resize:
            self._sync_height_to_width()
        return super().eventFilter(obj, event)

    def sizeHint(self) -> QtCore.QSize:
        width = 480
        height = int(width * self._aspect_ratio)
        return QtCore.QSize(width, height)

    def _install_parent_filter(self) -> None:
        if self._parent_filter_installed:
            return
        parent = self.parentWidget()
        if parent is not None:
            parent.installEventFilter(self)
            self._parent_filter_installed = True

    def _sync_height_to_width(self) -> None:
        width = max(self._available_width() - 2, 1)
        height = int(width * self._aspect_ratio)
        if self.height() != height:
            self.setFixedHeight(height)

    def _available_width(self) -> int:
        parent = self.parentWidget()
        if parent is None:
            return self.width()
        width = parent.width()
        layout = parent.layout()
        if layout is not None:
            margins = layout.contentsMargins()
            width -= (margins.left() + margins.right())
        return max(width, 1)

    def load_svg_content(self, svg: str) -> None:
        if not svg:
            self._logger.warning("Empty SVG content for card %s", self.guid)
            return
        self._view.load(QtCore.QByteArray(svg.encode("utf-8")))


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
        return {
            "status": "error",
            "message": message,
            "hint": instructions,
        }

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

    @server.tool(name=_tool_name("RenderSVG"))
    def RenderSVG(GUID: str, svg_markup: str) -> dict:
        """Render SVG into an existing card."""
        card = cards.get(GUID)
        if not card:
            return _error("Card not found. Use CreateCard first to obtain a GUID.")

        svg_error = validate_svg(svg_markup)
        if svg_error:
            return _error(svg_error)

        svg_markup, missing = replace_resource_refs(svg_markup)
        if missing:
            missing_list = ", ".join(sorted(set(missing)))
            return _error(f"Resource image not found: {missing_list}")

        def _draw() -> None:
            card.load_svg_content(svg_markup)

        ui_invoke(_draw)
        return {"status": "ok", "guid": GUID}


__all__ = ["register_tools", "get_instructions", "SVGCard"]

MCP_TOOL_NAMES = ["CreateCard", "RenderSVG", "DeleteCard"]


def get_tool_names() -> list[str]:
    return list(MCP_TOOL_NAMES)

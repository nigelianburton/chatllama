from __future__ import annotations

import base64
import re
import uuid
from pathlib import Path
from typing import Callable, Optional, Any

from PyQt6 import QtCore, QtGui, QtWidgets, QtSvgWidgets

from Engine.logger import get_logger


RESOURCES_DIR = Path(__file__).resolve().parents[1] / "resources"
RESOURCE_SCHEME = "resource:"

INTERNAL_MCP_INSTRUCTIONS = (
    "You can only use these tools: CreateCard, DrawCard, DeleteCard. "
    "You MUST call CreateCard first to get a guid; never invent or guess guids. "
    "CreateCard returns a response with a guid field. "
    "Then pass that exact guid to DrawCard. "
    "DrawCard requires full SVG markup with a <svg> root sized 480x640 (portrait) or 640x480 (landscape). "
    "Never output SVG in assistant messages; only provide svg_instructions inside the DrawCard tool call arguments. "
    "After DrawCard succeeds, reply with a brief confirmation and do not call DrawCard again unless the user requests changes. "
    "For images, use href values like resource:pic1-portrait.jpg or resource:pic2-landscape.jpg (from the resources folder). "
    "Do not embed base64 images in prompts. Do not call any other tools."
)


def get_instructions() -> str:
    return INTERNAL_MCP_INSTRUCTIONS


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
) -> None:
    def _error(message: str) -> dict[str, str]:
        return {
            "status": "error",
            "message": message,
            "hint": INTERNAL_MCP_INSTRUCTIONS,
        }

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

    def _replace_resource_refs(svg: str) -> tuple[str, list[str]]:
        missing: list[str] = []

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

    def _validate_svg(svg: str) -> str | None:
        if not svg:
            return "SVG must be full <svg> markup. Include a <svg> root element and closing </svg>."
        trimmed = svg.strip()
        if not trimmed.startswith("<svg") or not trimmed.endswith("</svg>"):
            return "svg_instructions must be ONLY a single <svg>...</svg> document with no extra text."
        if "<svg" not in trimmed or "</svg>" not in trimmed:
            return "SVG must be full <svg> markup. Include a <svg> root element and closing </svg>."
        return None

    @server.tool()
    def CreateCard(isPortrait: bool = True) -> str | dict:
        """Create an SVG card and return its GUID.

        Use this first for any SVG request to obtain a GUID.
        Cards are always 480x640 (portrait) or 640x480 (landscape).
        Returns: {"status": "ok", "guid": "..."}.
        Do not output SVG in chat; use DrawCard with svg_instructions.
        """
        guid = str(uuid.uuid4())

        def _create() -> SVGCard:
            return ui_create_card(guid, isPortrait)

        card = ui_invoke(_create)
        if not isinstance(card, SVGCard):
            return _error("UI did not return SVGCard")
        cards[guid] = card
        return {"status": "ok", "guid": guid}

    @server.tool()
    def DeleteCard(GUID: str) -> dict:
        """Delete an SVG card by GUID.

        Returns: {"status": "ok", "guid": "..."}.
        """
        card = cards.get(GUID)
        if not card:
            return _error("Card not found. Use CreateCard first to obtain a GUID.")

        def _delete() -> None:
            ui_delete_card(card)

        ui_invoke(_delete)
        cards.pop(GUID, None)
        return {"status": "ok", "guid": GUID}

    @server.tool()
    def DrawCard(GUID: str, svg_instructions: str) -> dict:
        """Render SVG into an existing card.

        The GUID must come from CreateCard; do not fabricate GUIDs.

        Always call CreateCard first, then pass its GUID into DrawCard.

        The svg_instructions should be full SVG markup and MUST be passed only in this tool call.
        For images, reference files in the resources folder using resource: filenames.
        Example (portrait magazine cover):

        <svg width="480" height="640" viewBox="0 0 480 640" xmlns="http://www.w3.org/2000/svg">
          <rect width="480" height="640" fill="#ffffff" stroke="#d4a373" stroke-width="8"/>
          <image href="resource:pic1-portrait.jpg" x="40" y="120" width="400" height="260" preserveAspectRatio="xMidYMid slice"/>
          <text x="240" y="80" font-family="Georgia" font-size="36" font-weight="bold" text-anchor="middle" fill="#2d2a26">Urban Light</text>
          <text x="240" y="110" font-family="Arial" font-size="14" text-anchor="middle" fill="#7a6f62">January 2026 • Special Design Issue</text>
          <text x="240" y="420" font-family="Arial" font-size="22" font-weight="bold" text-anchor="middle" fill="#2d2a26">Inside the New Studio Wave</text>
          <text x="240" y="450" font-family="Arial" font-size="14" text-anchor="middle" fill="#7a6f62">Profiles • Trends • Tools</text>
          <rect x="320" y="500" width="120" height="100" fill="#f2f2f2" stroke="#cfcfcf"/>
          <text x="380" y="560" font-family="Arial" font-size="12" text-anchor="middle" fill="#666">Inset Photo</text>
        </svg>

        Returns: {"status": "ok", "guid": "..."}.
        """
        card = cards.get(GUID)
        if not card:
            return _error("Card not found. Use CreateCard first to obtain a GUID.")

        svg_error = _validate_svg(svg_instructions)
        if svg_error:
            return _error(svg_error)

        svg_instructions, missing = _replace_resource_refs(svg_instructions)
        if missing:
            missing_list = ", ".join(sorted(set(missing)))
            return _error(f"Resource image not found: {missing_list}")

        def _draw() -> None:
            card.load_svg_content(svg_instructions)

        ui_invoke(_draw)
        return {"status": "ok", "guid": GUID}

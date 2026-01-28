from __future__ import annotations

from typing import Any, Callable
from pathlib import Path
from urllib.parse import urlparse
import re

from PyQt6 import QtCore, QtGui, QtWidgets, QtWebEngineWidgets

from Engine.logger import get_logger
from MCP_Internal.mcp_card_helper import register_create_delete_tools


INTERNAL_MCP_INSTRUCTIONS_TEMPLATE = (
    "You can only use these tools: {create_tool}, {draw_tool}, {delete_tool}. "
    "You MUST call {create_tool} first to get a guid; never invent or guess guids. "
    "{create_tool} returns a response with a guid field. "
    "Then pass that exact guid to {draw_tool}. "
    "{draw_tool} accepts a single string that can be a URL, a local file path, or raw HTML. "
    "Never output HTML in assistant messages; only provide HTML inside the {draw_tool} tool call arguments. "
    "After {draw_tool} succeeds, reply with a brief confirmation and do not call it again unless the user requests changes."
)


def get_instructions(name_prefix: str | None = None) -> str:
    prefix = f"{name_prefix}." if name_prefix else ""
    return INTERNAL_MCP_INSTRUCTIONS_TEMPLATE.format(
        create_tool=f"{prefix}CreateCard",
        draw_tool=f"{prefix}DrawCard",
        delete_tool=f"{prefix}DeleteCard",
    )


def validate_draw_content(content: str) -> str | None:
    if not content or not str(content).strip():
        return "Draw content must not be empty."
    return None


class WebCard(QtWidgets.QFrame):
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

        self._view = QtWebEngineWidgets.QWebEngineView(self)
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

    def load_url(self, url: str) -> None:
        qurl = QtCore.QUrl.fromUserInput(url)
        if not qurl.isValid():
            self._logger.warning("Invalid URL for card %s: %s", self.guid, url)
            return
        self._view.load(qurl)

    def load_html(self, html: str, base_url: str | None = None) -> None:
        if base_url:
            base = QtCore.QUrl.fromUserInput(base_url)
            self._view.setHtml(html, base)
        else:
            self._view.setHtml(html)


def register_tools(
    server: Any,
    ui_invoke: Callable[[Callable[[], object]], object],
    ui_create_card: Callable[..., WebCard],
    ui_delete_card: Callable[[WebCard], None],
    cards: dict[str, WebCard],
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
        card_cls=WebCard,
        error_factory=_error,
        create_card=lambda guid, is_portrait: ui_create_card(guid, is_portrait, "web"),
        card_label="card",
    )

    def _looks_like_html(value: str) -> bool:
        lowered = value.lstrip().lower()
        if lowered.startswith("<"):
            return True
        return any(marker in lowered[:200] for marker in ("<html", "<!doctype", "<body", "<div", "<span", "<p", "<head", "<style", "<script"))

    def _looks_like_url(value: str) -> bool:
        parsed = urlparse(value)
        if parsed.scheme in ("http", "https", "file"):
            return True
        return bool(re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}([/?#].*)?$", value))

    @server.tool(name=_tool_name("DrawCard"))
    def DrawCard(GUID: str, content: str) -> dict:
        """Render URL, file path, or HTML into an existing web card."""
        card = cards.get(GUID)
        if not card:
            return _error("Card not found. Use CreateCard first to obtain a GUID.")

        content_error = validate_draw_content(content)
        if content_error:
            return _error(content_error)

        stripped = content.strip()
        path = Path(stripped).expanduser()

        if _looks_like_html(stripped):
            def _render_html() -> None:
                card.load_html(stripped)

            ui_invoke(_render_html)
            return {"status": "ok", "guid": GUID}

        if path.exists():
            def _load_file() -> None:
                card.load_url(path.resolve().as_uri())

            ui_invoke(_load_file)
            return {"status": "ok", "guid": GUID}

        if _looks_like_url(stripped):
            url = stripped
            if not urlparse(url).scheme:
                url = f"https://{url}"

            def _load_url() -> None:
                card.load_url(url)

            ui_invoke(_load_url)
            return {"status": "ok", "guid": GUID}

        def _render_html_fallback() -> None:
            card.load_html(stripped)

        ui_invoke(_render_html_fallback)
        return {"status": "ok", "guid": GUID}


__all__ = ["register_tools", "get_instructions", "WebCard"]

MCP_TOOL_NAMES = ["CreateCard", "DrawCard", "DeleteCard"]


def get_tool_names() -> list[str]:
    return list(MCP_TOOL_NAMES)

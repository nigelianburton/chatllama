from __future__ import annotations

from typing import Any, Callable
import tempfile
from pathlib import Path
from urllib.parse import urlparse, unquote
import base64
import re

from PyQt6 import QtCore, QtGui, QtWidgets, QtWebEngineWidgets, QtWebEngineCore

from Engine.logger import get_logger
from MCP_Internal.mcp_card_helper import register_create_delete_tools
RESOURCES_DIR = Path(__file__).resolve().parents[1] / "resources"
RESOURCE_SCHEME = "resource:"



INTERNAL_MCP_INSTRUCTIONS_TEMPLATE = (
    "## Web Card Rules\n"
    "1. **Workflow**: {create_tool} (returns GUID) -> {draw_tool} (uses GUID).\n"
    "2. **Content**: {draw_tool} accepts a URL, local file path, or raw HTML string.\n"
    "3. **Strict Constraint**: Use {draw_tool} ONLY for web content or full HTML docs. PROHIBITED for plain text or simple SVG icons.\n"
    "4. **Assistant Output**: Confirm tool success briefly. Never output raw HTML in chat."
)


def get_instructions(name_prefix: str | None = None) -> str:
    prefix = f"{name_prefix}." if name_prefix else ""
    return INTERNAL_MCP_INSTRUCTIONS_TEMPLATE.format(
        create_tool=f"{prefix}CreateCard",
        draw_tool=f"{prefix}RenderWeb",
        delete_tool=f"{prefix}DeleteCard",
    )


def validate_draw_content(content: str) -> str | None:
    if not content or not str(content).strip():
        return "Draw content must not be empty."
    return None


def _path_to_data_uri(path: Path) -> str:
    data = path.read_bytes()
    ext = path.suffix.lower()
    mime = "image/jpeg" if ext in {".jpg", ".jpeg"} else "image/png"
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _resource_to_data_uri(resource_value: str) -> str | None:
    name = resource_value[len(RESOURCE_SCHEME) :].lstrip("/")
    name = Path(name).name
    if not name:
        return None
    path = RESOURCES_DIR / name
    if not path.exists():
        return None
    return _path_to_data_uri(path)


def _file_url_to_path(value: str) -> Path | None:
    parsed = urlparse(value)
    if parsed.scheme != "file":
        return None
    raw_path = unquote(parsed.path)
    if parsed.netloc:
        return Path(f"//{parsed.netloc}{raw_path}")
    return Path(raw_path.lstrip("/"))


def replace_embedded_image_refs(html: str) -> tuple[str, list[str]]:
    missing: list[str] = []

    def _replace(match: re.Match[str]) -> str:
        attr = match.group("attr")
        quote = match.group("quote")
        value = match.group("value")
        if value.startswith(RESOURCE_SCHEME):
            data_uri = _resource_to_data_uri(value)
            if data_uri is None:
                missing.append(value)
                return match.group(0)
            return f"{attr}={quote}{data_uri}{quote}"
        if value.startswith("file:"):
            path = _file_url_to_path(value)
            if path is None or not path.exists():
                missing.append(value)
                return match.group(0)
            return f"{attr}={quote}{_path_to_data_uri(path)}{quote}"
        return match.group(0)

    pattern = r"(?P<attr>src|href)=(?P<quote>['\"])(?P<value>[^'\"]+)(?P=quote)"
    updated = re.sub(pattern, _replace, html)
    return updated, missing


class WebCard(QtWidgets.QFrame):
    def __init__(self, guid: str, is_portrait: bool) -> None:
        super().__init__()
        self._logger = get_logger(self)
        self.guid = guid
        self.is_portrait = is_portrait

        width, height = (480, 640) if is_portrait else (640, 480)
        self._base_size = QtCore.QSize(width, height)
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
        settings = self._view.settings()
        settings.setAttribute(
            QtWebEngineCore.QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls,
            True,
        )
        settings.setAttribute(
            QtWebEngineCore.QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
            True,
        )
        settings.setAttribute(
            QtWebEngineCore.QWebEngineSettings.WebAttribute.AllowRunningInsecureContent,
            True,
        )
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

    def grab_card_pixmap(self) -> QtGui.QPixmap:
        self._sync_height_to_width()
        try:
            target_size = self.size()
            if target_size.width() <= 1 or target_size.height() <= 1:
                target_size = self._base_size
            self.resize(target_size)
            self._view.resize(target_size)
            self._view.page().setViewportSize(target_size)
            self.setVisible(True)
            self._view.setVisible(True)
            self._view.show()
        except Exception:
            pass
        self._view.update()
        QtWidgets.QApplication.processEvents()
        self._wait_for_render(timeout_ms=3000)
        QtWidgets.QApplication.processEvents()
        page = self._view.page()
        page_grab = getattr(page, "grab", None)
        if callable(page_grab):
            try:
                page_pixmap = page_grab()
                if isinstance(page_pixmap, QtGui.QPixmap) and not page_pixmap.isNull():
                    return page_pixmap
            except Exception:
                pass
        pixmap = QtGui.QPixmap(self._view.size())
        pixmap.fill(QtGui.QColor("white"))
        painter = QtGui.QPainter(pixmap)
        try:
            self._view.render(painter)
        finally:
            painter.end()
        if pixmap.isNull():
            QtWidgets.QApplication.processEvents()
            pixmap = self._view.grab()
        return pixmap

    def load_url(self, url: str, *, wait_for_load: bool = False, timeout_ms: int = 3000) -> None:
        qurl = QtCore.QUrl.fromUserInput(url)
        if not qurl.isValid():
            self._logger.warning("Invalid URL for card %s: %s", self.guid, url)
            return
        self._view.load(qurl)
        if wait_for_load:
            self._wait_for_load(timeout_ms)
            self._wait_for_render(timeout_ms=1500)

    def load_html(
        self,
        html: str,
        base_url: str | None = None,
        *,
        wait_for_load: bool = False,
        timeout_ms: int = 3000,
    ) -> None:
        if base_url:
            base = QtCore.QUrl.fromUserInput(base_url)
            self._view.setHtml(html, base)
        else:
            self._view.setHtml(html)
        if wait_for_load:
            self._wait_for_load(timeout_ms)
            self._wait_for_render(timeout_ms=1500)

    def _wait_for_load(self, timeout_ms: int) -> None:
        loop = QtCore.QEventLoop()

        def _done(*_args) -> None:
            if loop.isRunning():
                loop.quit()

        self._view.loadFinished.connect(_done)
        QtCore.QTimer.singleShot(timeout_ms, loop.quit)
        loop.exec()
        try:
            self._view.loadFinished.disconnect(_done)
        except Exception:
            pass

    def _wait_for_render(self, timeout_ms: int = 1500) -> None:
        loop = QtCore.QEventLoop()
        done = {"value": False}

        script = (
            "(function(){"
            "const ready=document.readyState==='complete';"
            "const imgs=Array.from(document.images||[]);"
            "const imagesReady=imgs.length===0 || imgs.every(i=>i.complete && i.naturalWidth>0);"
            "return ready && imagesReady;"
            "})();"
        )

        def _finish() -> None:
            done["value"] = True
            if loop.isRunning():
                loop.quit()

        def _handle(result: Any) -> None:
            if result:
                _finish()
            else:
                QtCore.QTimer.singleShot(100, _check)

        def _check() -> None:
            if done["value"]:
                return
            try:
                self._view.page().runJavaScript(script, _handle)
            except Exception:
                _finish()

        _check()
        QtCore.QTimer.singleShot(timeout_ms, loop.quit)
        loop.exec()


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

    @server.tool(name=_tool_name("RenderWeb"))
    def RenderWeb(GUID: str, web_content: str) -> dict:
        """Render URL, file path, or HTML into an existing web card."""
        card = cards.get(GUID)
        if not card:
            return _error("Card not found. Use CreateCard first to obtain a GUID.")
        if not isinstance(card, WebCard) and card.__class__.__name__ != WebCard.__name__:
            return _error("Card type mismatch. Create a web card with CreateCard before calling RenderWeb.")

        content_error = validate_draw_content(web_content)
        if content_error:
            return _error(content_error)

        stripped = web_content.strip()
        path = Path(stripped).expanduser()

        if _looks_like_html(stripped):
            rendered_html, missing = replace_embedded_image_refs(stripped)
            if missing:
                missing_list = ", ".join(sorted(set(missing)))
                return _error(f"Resource image not found: {missing_list}")

            def _render_html() -> None:
                try:
                    temp_path = Path(tempfile.gettempdir()) / f"web_card_{GUID}.html"
                    temp_path.write_text(rendered_html, encoding="utf-8")
                    card.load_url(temp_path.as_uri(), wait_for_load=True, timeout_ms=6000)
                except Exception:
                    card.load_html(rendered_html, base_url=RESOURCES_DIR.resolve().as_uri(), wait_for_load=True, timeout_ms=6000)

            ui_invoke(_render_html)
            return {"status": "ok", "guid": GUID}

        if path.exists():
            def _load_file() -> None:
                card.load_url(path.resolve().as_uri(), wait_for_load=True)

            ui_invoke(_load_file)
            return {"status": "ok", "guid": GUID}

        if _looks_like_url(stripped):
            url = stripped
            if not urlparse(url).scheme:
                url = f"https://{url}"

            def _load_url() -> None:
                card.load_url(url, wait_for_load=True)

            ui_invoke(_load_url)
            return {"status": "ok", "guid": GUID}

        rendered_html, missing = replace_embedded_image_refs(stripped)
        if missing:
            missing_list = ", ".join(sorted(set(missing)))
            return _error(f"Resource image not found: {missing_list}")

        def _render_html_fallback() -> None:
            card.load_html(rendered_html, wait_for_load=True)

        ui_invoke(_render_html_fallback)
        return {"status": "ok", "guid": GUID}


__all__ = ["register_tools", "get_instructions", "WebCard"]

MCP_TOOL_NAMES = ["CreateCard", "RenderWeb", "DeleteCard"]


def get_tool_names() -> list[str]:
    return list(MCP_TOOL_NAMES)

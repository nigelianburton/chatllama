from typing import Any, Dict, List, Optional
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtWebEngineWidgets import QWebEngineView
from ._card_template import CardBase
import logging

logger = logging.getLogger(__name__)


class CardChrome(CardBase):
    """Card that hosts a Chromium-based browser via QWebEngineView."""

    name: str = "card_chrome"
    functions: List[Dict[str, Any]] = [
        {
            "name": "open_url",
            "description": "Load the given URL into the embedded browser pane.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Absolute URL to load",
                    }
                },
                "required": ["url"],
            },
        }
    ]

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, start_url: str = "https://example.com") -> None:
        logger.info(f"[CardChrome] __init__ called with parent: {parent.__class__.__name__ if parent else None}")
        super().__init__(parent)
        logger.info(f"[CardChrome] After super().__init__, CardBase size: {self.size()}")
        
        self._view = QWebEngineView(self)
        logger.info(f"[CardChrome] Created QWebEngineView: {self._view}")
        
        self._view.setSizePolicy(
            QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        )
        # Set background color so we can see the browser
        self._view.setStyleSheet("QWebEngineView { background-color: yellow; }")
        self._view.setMinimumHeight(200)
        logger.info(f"[CardChrome] QWebEngineView configured. Size: {self._view.size()}, minHeight: {self._view.minimumHeight()}")
        
        self.set_card_widget(self._view)
        logger.info(f"[CardChrome] After set_card_widget. View parent: {self._view.parent().__class__.__name__ if self._view.parent() else None}")
        
        self.load_url(start_url)
        logger.info(f"[CardChrome] __init__ complete. URL: {start_url}")

    def load_url(self, url: str) -> None:
        if not url:
            return
        logger.info(f"[CardChrome] load_url called with: {url}")
        if hasattr(self._view, 'setUrl'):
            # Try loading a data URL with HTML content
            html_content = """<!DOCTYPE html><html><head><style>
            body { background: green; color: white; font-family: Arial; font-size: 24px; padding: 20px; margin: 0; }
            h1 { font-size: 48px; }
            </style></head><body><h1>✓ BROWSER WORKS!</h1><p>QWebEngineView is rendering HTML!</p></body></html>"""
            # Encode as data URL
            from urllib.parse import quote
            data_url = f"data:text/html,{quote(html_content)}"
            self._view.setUrl(QtCore.QUrl(data_url))
            logger.info(f"[CardChrome] Data URL loaded with green page")
        else:
            logger.info(f"[CardChrome] View does not support setUrl")
    
    def showEvent(self, event):
        super().showEvent(event)
        logger.info(f"[CardChrome] showEvent: size = {self.size()}, view size = {self._view.size()}")
        logger.info(f"[CardChrome] View visible: {self._view.isVisible()}, geometry: {self._view.geometry()}")

    def call(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        args = arguments or {}
        if name == "open_url":
            self.load_url(str(args.get("url", "https://example.com")))
            return {"status": "ok", "url": args.get("url")}
        raise ValueError(f"Unsupported function: {name}")

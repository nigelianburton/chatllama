from typing import Any, Dict, List, Optional
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtWebEngineWidgets import QWebEngineView
from ._card_template import CardBase


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
        super().__init__(parent)
        self._view = QWebEngineView(self)
        self._view.setSizePolicy(
            QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        )
        self.set_card_widget(self._view)
        self.load_url(start_url)

    def load_url(self, url: str) -> None:
        if not url:
            return
        self._view.setUrl(QtCore.QUrl(url))

    def call(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        args = arguments or {}
        if name == "open_url":
            self.load_url(str(args.get("url", "https://example.com")))
            return {"status": "ok", "url": args.get("url")}
        raise ValueError(f"Unsupported function: {name}")

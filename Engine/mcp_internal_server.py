from __future__ import annotations

import threading
import uuid
from typing import Callable, Optional

from Engine.logger import get_logger
from MCP_Internal.svg_card import SVGCard

try:
    from fastmcp.server import FastMCP
except Exception:  # pragma: no cover
    FastMCP = None  # type: ignore


class InternalMcpServer:
    def __init__(
        self,
        ui_invoke: Callable[[Callable[[], object]], object],
        ui_create_card: Callable[[str, bool], SVGCard],
        ui_delete_card: Callable[[SVGCard], None],
        host: str = "127.0.0.1",
        port: int = 6821,
    ) -> None:
        self._host = host
        self._port = port
        self._thread: Optional[threading.Thread] = None
        self._logger = get_logger(self)
        self._ui_invoke = ui_invoke
        self._ui_create_card = ui_create_card
        self._ui_delete_card = ui_delete_card
        self._cards: dict[str, SVGCard] = {}

    def start(self) -> None:
        if FastMCP is None:
            self._logger.error("fastmcp is not available; cannot start MCP server")
            raise RuntimeError("fastmcp is not available; cannot start MCP server")

        server = FastMCP("chatllama-internal")

        @server.tool()
        def CreateCard(isPortrait: bool = True) -> str:
            """Create an SVG card and return its GUID.

            Cards are always 480x640 (portrait) or 640x480 (landscape).
            Returns: GUID string for the card.
            """
            guid = str(uuid.uuid4())

            def _create() -> SVGCard:
                return self._ui_create_card(guid, isPortrait)

            card = self._ui_invoke(_create)
            if not isinstance(card, SVGCard):
                raise RuntimeError("UI did not return SVGCard")
            self._cards[guid] = card
            return guid

        @server.tool()
        def DeleteCard(GUID: str) -> dict:
            """Delete an SVG card by GUID."""
            card = self._cards.get(GUID)
            if not card:
                return {"status": "error", "message": "Card not found"}

            def _delete() -> None:
                self._ui_delete_card(card)

            self._ui_invoke(_delete)
            self._cards.pop(GUID, None)
            return {"status": "ok", "guid": GUID}

        @server.tool()
        def DrawCard(GUID: str, svg_instructions: str) -> dict:
            """Render SVG into an existing card.

            The svg_instructions should be full SVG markup. Example (portrait magazine cover):

            <svg width="480" height="640" viewBox="0 0 480 640" xmlns="http://www.w3.org/2000/svg">
              <rect width="480" height="640" fill="#ffffff" stroke="#d4a373" stroke-width="8"/>
              <image href="data:image/png;base64,...." x="40" y="120" width="400" height="260" preserveAspectRatio="xMidYMid slice"/>
              <text x="240" y="80" font-family="Georgia" font-size="36" font-weight="bold" text-anchor="middle" fill="#2d2a26">Urban Light</text>
              <text x="240" y="110" font-family="Arial" font-size="14" text-anchor="middle" fill="#7a6f62">January 2026 • Special Design Issue</text>
              <text x="240" y="420" font-family="Arial" font-size="22" font-weight="bold" text-anchor="middle" fill="#2d2a26">Inside the New Studio Wave</text>
              <text x="240" y="450" font-family="Arial" font-size="14" text-anchor="middle" fill="#7a6f62">Profiles • Trends • Tools</text>
              <rect x="320" y="500" width="120" height="100" fill="#f2f2f2" stroke="#cfcfcf"/>
              <text x="380" y="560" font-family="Arial" font-size="12" text-anchor="middle" fill="#666">Inset Photo</text>
            </svg>
            """
            card = self._cards.get(GUID)
            if not card:
                return {"status": "error", "message": "Card not found"}

            def _draw() -> None:
                card.load_svg_content(svg_instructions)

            self._ui_invoke(_draw)
            return {"status": "ok", "guid": GUID}

        def _run() -> None:
            self._logger.info("Starting FastMCP HTTP server on http://%s:%s", self._host, self._port)
            server.run(
                transport="http",
                host=self._host,
                port=self._port,
            )

        thread = threading.Thread(target=_run, name="MCP-HTTP", daemon=True)
        thread.start()
        self._thread = thread

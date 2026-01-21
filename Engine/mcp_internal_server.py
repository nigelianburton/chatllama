from __future__ import annotations

import threading
from typing import Callable, Optional

from Engine.logger import get_logger
from MCP_Internal.svg_card import SVGCard, register_tools, get_instructions

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

        server = FastMCP("chatllama-internal", instructions=get_instructions())

        register_tools(
            server=server,
            ui_invoke=self._ui_invoke,
            ui_create_card=self._ui_create_card,
            ui_delete_card=self._ui_delete_card,
            cards=self._cards,
        )

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

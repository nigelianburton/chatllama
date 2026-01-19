import json
import logging
import threading
import uuid
from pathlib import Path
from typing import Callable, Optional

try:
    from fastmcp.server import FastMCP
except Exception:
    FastMCP = None  # type: ignore

logger = logging.getLogger(__name__)


class ChatLlamaMCPServer:
    """Built-in FastMCP HTTP server to let LLMs generate page layouts (SVG)."""

    def __init__(
        self,
        ui_display_svg: Callable[[str], None],
        rules_path: Path,
        host: str = "127.0.0.1",
        port: int = 6821,
    ) -> None:
        self._ui_display_svg = ui_display_svg
        self._rules_path = rules_path
        self._host = host
        self._port = port
        self._server: Optional[FastMCP] = None
        self._thread: Optional[threading.Thread] = None

    def _load_rules(self) -> dict:
        try:
            with open(self._rules_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load SVG generation rules: {e}")
            return {"svg_generation_rules": {"note": "rules unavailable"}}

    def start(self) -> bool:
        if FastMCP is None:
            logger.error("fastmcp not available; cannot start MCP HTTP server")
            return False

        server = FastMCP("svg-layout-studio")  # clear name for LLMs
        rules_json = self._load_rules()

        @server.tool()
        def create_artboard(
            orientation: str = "portrait",
            width: Optional[int] = None,
            height: Optional[int] = None,
        ) -> dict:
            """Create an artboard (canvas) for layout work; MUST be first step.

            Returns a GUID and attaches directive SVG rules to guide small models.
            """
            orient = (orientation or "portrait").lower()
            if width is None or height is None:
                if orient == "landscape":
                    width, height = 1400, 1000
                else:
                    width, height = 1000, 1400

            artboard_guid = str(uuid.uuid4())
            return {
                "artboard_guid": artboard_guid,
                "width": width,
                "height": height,
                "orientation": orient,
                "viewBox": f"0 0 {width} {height}",
                "rules": rules_json,  # attach only on demand via tool response
            }

        @server.tool()
        def render_svg(artboard_guid: str, svg: str) -> dict:
            """Render an SVG to the UI cards panel and return status."""
            try:
                # Schedule render into the UI
                self._ui_display_svg(svg)
                return {
                    "status": "ok",
                    "artboard_guid": artboard_guid,
                    "length": len(svg),
                }
            except Exception as e:
                logger.error(f"render_svg failed: {e}")
                return {"status": "error", "message": str(e)}

        @server.tool()
        def list_svg_capabilities() -> dict:
            """Summarize available SVG-related tools for discoverability."""
            return {
                "tools": [
                    {
                        "name": "create_artboard",
                        "description": "Create an SVG canvas (artboard) and receive strict SVG rules",
                        "first_step": True,
                    },
                    {
                        "name": "render_svg",
                        "description": "Render provided SVG markup into the user's UI",
                        "requires": ["artboard_guid"],
                    },
                ]
            }

        self._server = server

        def _run():
            try:
                logger.info(
                    f"Starting built-in MCP HTTP server (svg-layout-studio) on http://{self._host}:{self._port}"
                )
                server.run(transport="sse", host=self._host, port=self._port)
            except Exception as e:
                logger.error(f"MCP HTTP server stopped: {e}")

        thread = threading.Thread(target=_run, name="MCP-HTTP", daemon=True)
        thread.start()
        self._thread = thread
        return True

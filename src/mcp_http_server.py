"""Built-in MCP server for SVG layout generation.

This server exposes tools that allow LLMs to create artboards and render SVG
into the Cards panel. It follows the same FastMCP decorator pattern as external
servers, but is automatically available without settings.yml configuration.
"""

import json
import logging
import threading
import uuid
from pathlib import Path
from typing import Callable, Optional, Dict, Any, List

try:
    from fastmcp.server import FastMCP
except Exception:
    FastMCP = None  # type: ignore

logger = logging.getLogger(__name__)


class SVGLayoutStudioMCP:
    """Built-in MCP server: svg-layout-studio.
    
    Provides tools for LLMs to create artboards and render SVG layouts.
    Automatically discovered and displayed alongside external MCPs.
    """

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
        self._tools_cache: Optional[List[Dict[str, Any]]] = None

    def _load_rules(self) -> dict:
        try:
            with open(self._rules_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load SVG generation rules: {e}")
            return {"svg_generation_rules": {"note": "rules unavailable"}}

    def get_server_config(self) -> Dict[str, Any]:
        """Return server configuration in settings.yml format for MCP panels."""
        return {
            "name": "svg-layout-studio",
            "type": "builtin",
            "url": f"http://{self._host}:{self._port}/sse",
            "description": "Built-in: Generate SVG page layouts",
        }

    def get_tools(self) -> List[Dict[str, Any]]:
        """Return tool definitions for advertising to LLM and displaying in UI.
        
        Returns tools in MCP format with inputSchema.
        """
        if self._tools_cache:
            return self._tools_cache

        rules_json = self._load_rules()
        
        tools = [
            {
                "name": "create_artboard",
                "description": "CREATE AN ARTBOARD (CANVAS) FIRST STEP BEFORE RENDERING SVG. This creates a blank canvas you will render your design on. Returns a GUID and SVG dimension rules. Always call this first, then use render_svg to display your design. Artboards are portrait (1000x1400px) or landscape (1400x1000px) by default.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "orientation": {
                            "type": "string",
                            "description": "Canvas orientation: 'portrait' for vertical designs (1000x1400px) or 'landscape' for horizontal designs (1400x1000px). Default: portrait",
                            "enum": ["portrait", "landscape"],
                            "default": "portrait"
                        },
                        "width": {
                            "type": "integer",
                            "description": "Canvas width in pixels (optional, auto-calculated from orientation). Typically 1000 (portrait) or 1400 (landscape)"
                        },
                        "height": {
                            "type": "integer",
                            "description": "Canvas height in pixels (optional, auto-calculated from orientation). Typically 1400 (portrait) or 1000 (landscape)"
                        }
                    }
                }
            },
            {
                "name": "render_svg",
                "description": "RENDER SVG DESIGN TO DISPLAY IN THE CARDS PANEL. Pass the artboard GUID from create_artboard and your complete SVG markup. This displays your design in the user's Cards panel. Use this after create_artboard to show your design.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "artboard_guid": {
                            "type": "string",
                            "description": "GUID returned by create_artboard (required). This identifies which artboard to render on."
                        },
                        "svg": {
                            "type": "string",
                            "description": "Complete SVG markup to render. Must be valid SVG with <svg> root element and viewBox attribute."
                        }
                    },
                    "required": ["artboard_guid", "svg"]
                }
            },
            {
                "name": "list_svg_capabilities",
                "description": "List available SVG tools and their capabilities. Returns information about create_artboard and render_svg.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]
        
        self._tools_cache = tools
        return tools

    def call_tool(self, tool_name: str, arguments: dict) -> Optional[Dict[str, Any]]:
        """Call a tool directly and return the result.
        
        This method allows synchronous execution of built-in tools without going
        through the FastMCP HTTP server.
        """
        logger.debug(f"Calling built-in tool: {tool_name} with {arguments}")
        
        try:
            if tool_name == "create_artboard":
                orient = (arguments.get("orientation", "portrait") or "portrait").lower()
                width = arguments.get("width")
                height = arguments.get("height")
                
                if width is None or height is None:
                    if orient == "landscape":
                        width, height = 1400, 1000
                    else:
                        width, height = 1000, 1400
                
                artboard_guid = str(uuid.uuid4())
                rules_json = self._load_rules()
                return {
                    "artboard_guid": artboard_guid,
                    "width": width,
                    "height": height,
                    "orientation": orient,
                    "viewBox": f"0 0 {width} {height}",
                    "rules": rules_json,
                }
                
            elif tool_name == "render_svg":
                artboard_guid = arguments.get("artboard_guid")
                svg = arguments.get("svg")
                
                if not artboard_guid or not svg:
                    return {"status": "error", "message": "Missing artboard_guid or svg"}
                
                try:
                    self._ui_display_svg(svg)
                    return {
                        "status": "ok",
                        "artboard_guid": artboard_guid,
                        "length": len(svg),
                    }
                except Exception as e:
                    logger.error(f"render_svg failed: {e}")
                    return {"status": "error", "message": str(e)}
                    
            elif tool_name == "list_svg_capabilities":
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
            else:
                logger.warning(f"Unknown tool: {tool_name}")
                return {"status": "error", "message": f"Unknown tool: {tool_name}"}
                
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return {"status": "error", "message": str(e)}

    def start(self) -> bool:
        """Start the FastMCP HTTP server in a background thread."""
        if FastMCP is None:
            logger.error("fastmcp not available; cannot start MCP HTTP server")
            return False

        server = FastMCP("svg-layout-studio")
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
                "rules": rules_json,
            }

        @server.tool()
        def render_svg(artboard_guid: str, svg: str) -> dict:
            """Render an SVG to the UI cards panel and return status."""
            try:
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

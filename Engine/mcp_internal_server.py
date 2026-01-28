from __future__ import annotations

import asyncio
import importlib.util
import threading
from pathlib import Path
from typing import Callable, Optional, Any

from Engine.logger import get_logger
from constants import INTERNAL_MCP_NAME
from MCP_Internal.card_svg import SVGCard

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
        self._server: Any | None = None
        self._shutting_down = False

    def start(self) -> None:
        if FastMCP is None:
            self._logger.error("fastmcp is not available; cannot start MCP server")
            raise RuntimeError("fastmcp is not available; cannot start MCP server")

        self._patch_sse_writer()

        mcp_modules = self._load_internal_mcps()
        instructions = self._build_instructions(mcp_modules)
        server = FastMCP("chatllama-internal", instructions=instructions or None)
        self._server = server

        for name, module in mcp_modules:
            register = getattr(module, "register_tools", None)
            if not callable(register):
                self._logger.warning("Internal MCP %s has no register_tools", name)
                continue
            try:
                register(
                    server=server,
                    ui_invoke=self._ui_invoke,
                    ui_create_card=self._ui_create_card,
                    ui_delete_card=self._ui_delete_card,
                    cards=self._cards,
                    name_prefix=name,
                )
            except TypeError:
                register(
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

    def stop(self) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True
        server = self._server
        if server is None:
            return

        for attr in ("shutdown", "close", "stop"):
            handler = getattr(server, attr, None)
            if not callable(handler):
                continue
            try:
                result = handler()
                if asyncio.iscoroutine(result):
                    asyncio.run(result)
            except Exception as exc:
                self._logger.warning("Failed to %s internal MCP server: %s", attr, exc)
            break

    def _patch_sse_writer(self) -> None:
        """Guard SSE writer during shutdown to avoid noisy ClosedResourceError logs."""
        try:
            from mcp.server import streamable_http
            from anyio import ClosedResourceError
        except Exception:
            return

        original = getattr(streamable_http, "standalone_sse_writer", None)
        if original is None:
            return

        if getattr(streamable_http, "_chatllama_patched", False):
            return

        async def _wrapped(*args, **kwargs):
            try:
                return await original(*args, **kwargs)
            except ClosedResourceError:
                return None

        streamable_http.standalone_sse_writer = _wrapped
        streamable_http._chatllama_patched = True

    def _load_internal_mcps(self) -> list[tuple[str, Any]]:
        internal_folder = Path(__file__).resolve().parents[1] / "MCP_Internal"
        modules: list[tuple[str, Any]] = []
        if not internal_folder.exists():
            return modules

        for entry in sorted(internal_folder.glob("mcp_*.py")):
            if entry.name == "__init__.py":
                continue
            name = entry.stem
            try:
                module = self._load_module(name, entry)
            except Exception as exc:
                self._logger.warning("Failed to load internal MCP %s: %s", name, exc)
                continue
            modules.append((name, module))
        return modules

    def _load_module(self, name: str, path: Path) -> Any:
        spec = importlib.util.spec_from_file_location(f"MCP_Internal.{name}", path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Could not load {name} from {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _build_instructions(self, modules: list[tuple[str, Any]]) -> str:
        parts: list[str] = []
        for name, module in modules:
            get_instructions = getattr(module, "get_instructions", None)
            if not callable(get_instructions):
                continue
            try:
                instruction = get_instructions(f"{INTERNAL_MCP_NAME}.{name}")
            except TypeError:
                instruction = get_instructions()
            if instruction:
                parts.append(instruction)
        return "\n\n".join(parts)

from __future__ import annotations

import asyncio
import importlib.util
import shutil
import socket
import urllib.parse
from pathlib import Path


class MCPController:
    def __init__(self, logger) -> None:
        self._logger = logger

    def load_internal_module(self, name: str, path: Path):
        spec = importlib.util.spec_from_file_location(f"MCP_Internal.{name}", path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Could not load internal MCP {name}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def get_internal_tool_names(self, module: object) -> list[str]:
        names = getattr(module, "MCP_TOOL_NAMES", None)
        if isinstance(names, list):
            return [str(name) for name in names]
        getter = getattr(module, "get_tool_names", None)
        if callable(getter):
            try:
                result = getter()
            except Exception:
                result = []
            if isinstance(result, list):
                return [str(name) for name in result]
        return []

    def get_internal_preamble(self, module: object, name: str) -> str:
        getter = getattr(module, "get_instructions", None)
        if not callable(getter):
            return ""
        try:
            return str(getter(name) or "")
        except TypeError:
            return str(getter() or "")

    def discover_stdio_methods(self, path: Path) -> list:
        from fastmcp import Client
        tools: list = []

        async def _run() -> None:
            async with Client(str(path)) as client:
                items = await client.list_tools()
                tools.extend(items)

        asyncio.run(_run())
        return tools

    def discover_http_methods(self, server_url: str) -> list:
        from fastmcp import Client
        tools: list = []

        async def _run() -> None:
            async with Client(server_url) as client:
                items = await client.list_tools()
                tools.extend(items)

        asyncio.run(_run())
        return tools

    def probe_http(self, url: str) -> bool:
        try:
            parsed = urllib.parse.urlparse(url)
            host = parsed.hostname
            if not host:
                return False
            port = parsed.port
            if port is None:
                port = 443 if parsed.scheme == "https" else 80
            with socket.create_connection((host, port), timeout=1.5):
                return True
        except Exception:
            return False

    def copy_mcp_file(self, source_path: Path, target_folder: Path) -> Path:
        target_folder.mkdir(parents=True, exist_ok=True)
        target_path = target_folder / source_path.name
        shutil.copy2(source_path, target_path)
        return target_path

    def delete_mcp_file(self, path: Path) -> None:
        if path.exists():
            path.unlink()

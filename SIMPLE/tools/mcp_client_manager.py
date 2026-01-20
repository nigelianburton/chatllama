from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any


class MCPClientManager:
    def __init__(self, server_source: str | Path | dict) -> None:
        self._server_source = server_source

    def list_tools(self) -> list[Any]:
        return asyncio.run(self._list_tools_async())

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        return asyncio.run(self._call_tool_async(name, arguments))

    async def _list_tools_async(self) -> list[Any]:
        from fastmcp import Client

        async with Client(self._server_source) as client:
            return await client.list_tools()

    async def _call_tool_async(self, name: str, arguments: dict[str, Any]) -> Any:
        from fastmcp import Client

        async with Client(self._server_source) as client:
            result = await client.call_tool(name, arguments)
            return getattr(result, "data", result)

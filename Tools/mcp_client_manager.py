from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
import json


class MCPClientManager:
    def __init__(self, server_source: str | Path | dict) -> None:
        self._server_source = server_source

    def list_tools(self, timeout: float | None = 3.0) -> list[Any]:
        return asyncio.run(self._list_tools_async(timeout))

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        return asyncio.run(self._call_tool_async(name, arguments))

    def get_instructions(self, timeout: float | None = 3.0) -> str | None:
        return asyncio.run(self._get_instructions_async(timeout))

    async def _list_tools_async(self, timeout: float | None) -> list[Any]:
        from fastmcp import Client

        async with Client(self._server_source) as client:
            if timeout is None:
                return await client.list_tools()
            return await asyncio.wait_for(client.list_tools(), timeout=timeout)

    async def _call_tool_async(self, name: str, arguments: dict[str, Any]) -> Any:
        from fastmcp import Client

        async with Client(self._server_source) as client:
            result = await client.call_tool(name, arguments)
            value = getattr(result, "data", result)
            return _normalize_result(value)

    async def _get_instructions_async(self, timeout: float | None) -> str | None:
        from fastmcp import Client

        async with Client(self._server_source) as client:
            if client.initialize_result is None:
                if timeout is None:
                    await client.initialize()
                else:
                    await asyncio.wait_for(client.initialize(), timeout=timeout)
            initialize_result = client.initialize_result
            instructions = getattr(initialize_result, "instructions", None)
            return instructions or None


def _normalize_result(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump()
        except Exception:
            pass
    if hasattr(value, "dict"):
        try:
            return value.dict()
        except Exception:
            pass
    try:
        json.dumps(value)
        return value
    except Exception:
        return str(value)

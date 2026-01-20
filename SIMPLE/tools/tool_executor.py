from __future__ import annotations

from typing import Any

from .mcp_client_manager import MCPClientManager

from .tool_protocol_base import ToolCall
from .tool_registry import ToolRegistry


class ToolExecutor:
    def __init__(self, registry: ToolRegistry, mcp_manager: MCPClientManager | None = None) -> None:
        self._registry = registry
        self._mcp_manager = mcp_manager

    def execute(self, tool_call: ToolCall) -> Any:
        tool = self._registry.get(tool_call.name)
        if tool is None:
            return {"error": "unknown tool", "name": tool_call.name}
        if tool.source == "mcp" and self._mcp_manager is not None:
            return self._mcp_manager.call_tool(tool_call.name, tool_call.arguments)
        return {"error": "tool execution not wired", "name": tool_call.name}

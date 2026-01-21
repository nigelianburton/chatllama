from __future__ import annotations

from typing import Any

from .mcp_client_manager import MCPClientManager

from .tool_protocol_base import ToolCall
from .tool_registry import ToolRegistry


class ToolExecutor:
    def __init__(
        self,
        registry: ToolRegistry,
        mcp_manager: MCPClientManager | None = None,
        mcp_tool_map: dict[str, tuple[MCPClientManager, str]] | None = None,
    ) -> None:
        self._registry = registry
        self._mcp_manager = mcp_manager
        self._mcp_tool_map = mcp_tool_map or {}

    def execute(self, tool_call: ToolCall) -> Any:
        tool = self._registry.get(tool_call.name)
        if tool is None:
            return {"error": "unknown tool", "name": tool_call.name}
        if not tool.enabled:
            return {"error": "tool disabled", "name": tool_call.name}
        if tool.source == "mcp":
            mapped = self._mcp_tool_map.get(tool_call.name)
            if mapped is not None:
                manager, tool_name = mapped
                return manager.call_tool(tool_name, tool_call.arguments)
            if self._mcp_manager is not None:
                return self._mcp_manager.call_tool(tool_call.name, tool_call.arguments)
        return {"error": "tool execution not wired", "name": tool_call.name}

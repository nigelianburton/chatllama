from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ToolDefinition:
    name: str
    schema: dict[str, Any]
    source: str
    enabled: bool = True


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def list_tools(self) -> list[dict[str, Any]]:
        return [tool.schema for tool in self._tools.values() if tool.enabled]

    def list_definitions(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Protocol


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]
    raw: str


class ToolProtocolAdapter(Protocol):
    def render_tools(self, tools: Iterable[dict[str, Any]], system_prompt: str | None = None) -> str:
        ...

    def parse_tool_calls(self, text: str) -> list[ToolCall]:
        ...

    def format_tool_result(self, tool_call: ToolCall, payload: Any) -> str:
        ...

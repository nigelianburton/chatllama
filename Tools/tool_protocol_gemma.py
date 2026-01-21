from __future__ import annotations

import json
import re
from typing import Any, Iterable

from .tool_protocol_base import ToolCall

_TOOL_JSON_RE = re.compile(r"\{\s*\"name\"\s*:\s*\"(?P<name>[^\"]+)\"\s*,\s*\"arguments\"\s*:\s*(?P<args>\{.*?\})\s*\}", re.DOTALL)


def render_tools(tools: Iterable[dict[str, Any]], system_prompt: str | None = None) -> str:
    prompt = system_prompt or ""
    if not tools:
        return prompt
    tools_json = json.dumps(list(tools))
    return f"{prompt}\nTOOLS_JSON:{tools_json}"


def parse_tool_calls(text: str) -> list[ToolCall]:
    calls: list[ToolCall] = []
    for match in _TOOL_JSON_RE.finditer(text):
        name = match.group("name")
        raw_args = match.group("args")
        try:
            args = json.loads(raw_args)
        except json.JSONDecodeError:
            args = {}
        calls.append(ToolCall(name=name, arguments=args, raw=match.group(0)))
    return calls


def format_tool_result(tool_call: ToolCall, payload: Any) -> str:
    return json.dumps({"tool": tool_call.name, "result": payload})

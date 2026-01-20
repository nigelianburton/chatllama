from __future__ import annotations

import json
import re
from typing import Any, Iterable

from .tool_protocol_base import ToolCall

_TOOL_BLOCK_RE = re.compile(r"\[TOOL_CALLS\](?P<body>.*?)\[\/TOOL_CALLS\]", re.DOTALL)
_CALL_RE = re.compile(r"(?P<name>[^\[]+)\[ARGS\](?P<args>\{.*?\})(?=\s|$)", re.DOTALL)


def render_tools(tools: Iterable[dict[str, Any]], system_prompt: str | None = None) -> str:
    prompt = system_prompt or ""
    if not tools:
        return prompt
    tools_json = json.dumps(list(tools))
    return f"{prompt}\n[AVAILABLE_TOOLS]{tools_json}[/AVAILABLE_TOOLS]"


def parse_tool_calls(text: str) -> list[ToolCall]:
    calls: list[ToolCall] = []
    block_match = _TOOL_BLOCK_RE.search(text)
    if not block_match:
        return calls
    body = block_match.group("body")
    for match in _CALL_RE.finditer(body):
        name = match.group("name").strip()
        raw_args = match.group("args")
        try:
            args = json.loads(raw_args)
        except json.JSONDecodeError:
            args = {}
        if name:
            calls.append(ToolCall(name=name, arguments=args, raw=match.group(0)))
    return calls


def format_tool_result(tool_call: ToolCall, payload: Any) -> str:
    return f"[TOOL_RESULTS]{json.dumps(payload)}[/TOOL_RESULTS]"

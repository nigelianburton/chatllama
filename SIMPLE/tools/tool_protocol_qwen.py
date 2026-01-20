from __future__ import annotations

import json
import re
from typing import Any, Iterable

from .tool_protocol_base import ToolCall

_TOOL_CALL_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)


def render_tools(tools: Iterable[dict[str, Any]], system_prompt: str | None = None) -> str:
    prompt = system_prompt or ""
    if not tools:
        return prompt
    tools_json = "\n".join(json.dumps(tool) for tool in tools)
    return f"{prompt}\n<tools>\n{tools_json}\n</tools>"


def parse_tool_calls(text: str) -> list[ToolCall]:
    calls: list[ToolCall] = []
    for match in _TOOL_CALL_RE.finditer(text):
        raw = match.group(1)
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        name = payload.get("name") or ""
        args = payload.get("arguments") or {}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}
        if name:
            calls.append(ToolCall(name=name, arguments=args, raw=raw))
    return calls


def format_tool_result(tool_call: ToolCall, payload: Any) -> str:
    return f"<tool_response>\n{json.dumps(payload)}\n</tool_response>"

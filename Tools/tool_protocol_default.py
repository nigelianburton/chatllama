from __future__ import annotations

import json
import re
from typing import Any, Iterable

from .tool_protocol_base import ToolCall

_TOOL_JSON_RE = re.compile(r"\{\s*\"name\"\s*:\s*\"(?P<name>[^\"]+)\"\s*,\s*\"arguments\"\s*:\s*(?P<args>\{.*?\})\s*\}", re.DOTALL)


def render_tools(tools: Iterable[dict[str, Any]], system_prompt: str | None = None) -> str:
    prompt = system_prompt or ""
    tools_list = list(tools)
    if not tools_list:
        return prompt
    tools_json = json.dumps(tools_list, indent=2)
    instructions = (
        "Tools are available. When you need to use a tool, respond with ONLY a JSON object in this exact format: "
        '{"name": "tool_name", "arguments": { ... }}. Do not include any other text.'
    )
    blocks = [prompt] if prompt else []
    blocks.append(instructions)
    blocks.append("Available tools (JSON):")
    blocks.append(tools_json)
    return "\n\n".join(blocks)


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
    return json.dumps({"name": tool_call.name, "result": payload})

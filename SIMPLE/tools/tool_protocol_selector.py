from __future__ import annotations

from typing import Callable

from .tool_protocol_base import ToolProtocolAdapter
from . import tool_protocol_default as default_adapter
from . import tool_protocol_gemma as gemma_adapter
from . import tool_protocol_huihui as huihui_adapter
from . import tool_protocol_qwen as qwen_adapter


def select_adapter(chat_template: str | None) -> ToolProtocolAdapter:
    template = chat_template or ""
    if "[AVAILABLE_TOOLS]" in template or "[TOOL_CALLS]" in template:
        return huihui_adapter
    if "<tool_call>" in template or "<tools>" in template:
        return qwen_adapter
    if "<start_of_turn>" in template:
        return gemma_adapter
    return default_adapter

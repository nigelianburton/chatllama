from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Callable, Iterable


class ChatController:
    def __init__(self, logger) -> None:
        self._logger = logger
        self._llama_module = None
        self._chat_server = None
        self._load_modules()

    def _load_modules(self) -> None:
        module_path = Path(__file__).resolve().parents[1] / "Engine" / "manager_models.py"
        spec = importlib.util.spec_from_file_location("manager_models", module_path)
        if spec is None or spec.loader is None:
            self._logger.error("Failed to load llamacpp-server module")
            return
        import sys
        model_module = sys.modules.get(spec.name)
        if model_module is None:
            model_module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = model_module
            spec.loader.exec_module(model_module)

        self._llama_module = model_module

        chat_module_path = Path(__file__).resolve().parents[1] / "Engine" / "manager_chats.py"
        chat_spec = importlib.util.spec_from_file_location("manager_chats", chat_module_path)
        if chat_spec is None or chat_spec.loader is None:
            self._logger.error("Failed to load chat manager module")
            return
        chat_module = sys.modules.get(chat_spec.name)
        if chat_module is None:
            chat_module = importlib.util.module_from_spec(chat_spec)
            sys.modules[chat_spec.name] = chat_module
            chat_spec.loader.exec_module(chat_module)

        try:
            self._chat_server = chat_module.LlamaChatManager()
        except Exception as exc:
            self._logger.exception("Failed to initialize chat server: %s", exc)
            self._chat_server = None

    @property
    def chat_server(self):
        return self._chat_server

    def register_callbacks(
        self,
        on_stream_chunk: Callable[[str], None],
        on_stream_end: Callable[[], None],
        on_tool_call: Callable[[object], None],
        on_tool_result: Callable[[object, object], None],
        on_followup: Callable[[], None],
        on_model_state: Callable[[str, object], None],
    ) -> bool:
        if self._chat_server is None or self._llama_module is None:
            self._logger.warning("Chat controller unavailable: missing modules")
            return False
        try:
            self._chat_server.register_stream_callback(on_stream_chunk)
            self._chat_server.register_stream_end_callback(on_stream_end)
            self._chat_server.register_tool_call_callback(on_tool_call)
            self._chat_server.register_tool_result_callback(on_tool_result)
            self._chat_server.register_followup_callback(on_followup)
            self._llama_module.register_model_state_callback(on_model_state)
            return True
        except Exception as exc:
            self._logger.exception("Failed to register chat callbacks: %s", exc)
            return False

    def register_availability_callback(self, callback: Callable[[str], None]) -> bool:
        if self._chat_server is None:
            return False
        try:
            self._chat_server.register_availability_callback(callback)
            return True
        except Exception:
            return False

    def send_message(self, text: str, image_paths: Iterable[Path]) -> None:
        if self._chat_server is None:
            return
        self._chat_server.send_message(text, image_paths=image_paths)

    def get_user_tool_names(self) -> list[str]:
        if self._chat_server is None:
            return []
        return self._chat_server.get_user_tool_names()

    def get_tools_advertisement(self):
        if self._chat_server is None:
            return None
        return self._chat_server.get_tools_advertisement()

    def reload_mcp_tools(self) -> None:
        if self._chat_server is None:
            return
        self._chat_server.reload_mcp_tools()

    def get_last_assistant_message(self) -> str:
        if self._chat_server is None:
            return ""
        return self._chat_server.get_last_assistant_message()

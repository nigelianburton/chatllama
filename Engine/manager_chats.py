from __future__ import annotations

import base64
import json
import mimetypes
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Optional

from Engine.logger import get_logger
from Engine.manager_models import (
    LLAMA_SERVER_HOST,
    LLAMA_SERVER_PORT,
    _fetch_loaded_model,
    _load_settings,
    _restart_router_with_preset,
    load_settings_fresh,
    register_model_state_callback,
    load_model,
)
from constants import INTERNAL_MCP_HOST, INTERNAL_MCP_NAME, INTERNAL_MCP_PORT
from Tools.mcp_client_manager import MCPClientManager
from Tools.tool_executor import ToolExecutor
from Tools.tool_protocol_base import ToolCall
from Tools.tool_protocol_selector import select_adapter
from Tools.tool_registry import ToolDefinition, ToolRegistry


class LlamaChatManager:
    def __init__(self, host: str = LLAMA_SERVER_HOST, port: int = LLAMA_SERVER_PORT) -> None:
        self._logger = get_logger(self)
        self._host = host
        self._port = port
        self._messages: list[dict] = []
        self._stream_callbacks: list[Callable[[str], None]] = []
        self._stream_end_callbacks: list[Callable[[], None]] = []
        self._tool_call_callbacks: list[Callable[[ToolCall], None]] = []
        self._tool_result_callbacks: list[Callable[[ToolCall, object], None]] = []
        self._followup_callbacks: list[Callable[[], None]] = []
        self._lock = threading.Lock()
        self._stream_log_buffer = ""
        self._adapter = select_adapter(self._get_chat_template())
        self._tool_registry = ToolRegistry()
        self._tool_schemas: list[dict] = []
        self._tool_server_instructions: dict[str, str] = {}
        self._tool_system_added = False
        self._tool_system_message: dict | None = None
        self._internal_card_guids: set[str] = set()
        self._internal_tools_enabled = False
        self._mcp_manager: MCPClientManager | None = None
        self._tool_executor: ToolExecutor | None = None
        self._mcp_load_lock = threading.Lock()
        self._mcp_loading = False
        self._mcp_tool_map: dict[str, tuple[MCPClientManager, str]] = {}
        self._load_mcp_tools_from_settings_async()
        self._availability_callbacks: list[Callable[[str], None]] = []
        self._availability_state = "BUSY"
        self._availability_lock = threading.Lock()
        self._active_request = False
        self._model_ready = False
        register_model_state_callback(self._on_model_state)

    @property
    def messages(self) -> list[dict]:
        return list(self._messages)

    def register_availability_callback(self, callback: Callable[[str], None]) -> None:
        self._availability_callbacks.append(callback)
        try:
            callback(self._availability_state)
        except Exception:
            pass

    def register_stream_callback(self, callback: Callable[[str], None]) -> None:
        self._stream_callbacks.append(callback)

    def register_stream_end_callback(self, callback: Callable[[], None]) -> None:
        self._stream_end_callbacks.append(callback)

    def register_tool_call_callback(self, callback: Callable[[ToolCall], None]) -> None:
        self._tool_call_callbacks.append(callback)

    def register_tool_result_callback(self, callback: Callable[[ToolCall, object], None]) -> None:
        self._tool_result_callbacks.append(callback)

    def register_followup_callback(self, callback: Callable[[], None]) -> None:
        self._followup_callbacks.append(callback)

    def reload_mcp_tools(self) -> None:
        self._load_mcp_tools_from_settings_async()

    def clear_messages(self) -> None:
        with self._lock:
            self._messages.clear()
        self._internal_card_guids.clear()
        self._set_internal_drawcard_enabled(False)

    def get_last_assistant_message(self) -> str:
        with self._lock:
            for message in reversed(self._messages):
                if message.get("role") != "assistant":
                    continue
                content = message.get("content", "")
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    parts = []
                    for item in content:
                        if not isinstance(item, dict):
                            continue
                        if item.get("type") == "text":
                            text = item.get("text")
                            if text:
                                parts.append(text)
                    return "\n".join(parts)
                return str(content)
        return ""

    def get_user_tool_names(self) -> list[str]:
        if not self._tool_schemas and not self._mcp_loading:
            self._load_mcp_tools_from_settings_async()
        tool_names: list[str] = []
        for schema in self._tool_schemas:
            function = schema.get("function") if isinstance(schema, dict) else None
            if isinstance(function, dict):
                name = function.get("name")
                if name:
                    tool_names.append(str(name))
        return tool_names

    def send_message(self, text: str, image_paths: Optional[list[Path]] = None) -> None:
        self._logger.info("User: %s", text)
        self._stream_log_buffer = ""
        self._adapter = select_adapter(self._get_chat_template())
        if not self._tool_schemas and not self._mcp_loading:
            self._load_mcp_tools_from_settings_async()
        if image_paths:
            for path in image_paths:
                self._logger.info("User attachment: %s", path)
        self._ensure_tool_system_message()
        if self._tool_schemas:
            self._logger.info("Tool schemas attached: %d", len(self._tool_schemas))
        tool_names: list[str] = []
        for schema in self._tool_schemas:
            function = schema.get("function") if isinstance(schema, dict) else None
            if isinstance(function, dict):
                name = function.get("name")
                if name:
                    tool_names.append(str(name))
        self._logger.info("User tools included: %s", ", ".join(tool_names) if tool_names else "none")
        content = self._build_content(text, image_paths or [])
        user_message = {"role": "user", "content": content}
        assistant_message = {"role": "assistant", "content": ""}

        with self._lock:
            self._messages.append(user_message)
            self._messages.append(assistant_message)

        self._active_request = True
        self._set_availability("BUSY")
        thread = threading.Thread(
            target=self._stream_completion,
            args=(assistant_message,),
            daemon=True,
        )
        self._logger.info("Starting chat completion thread")
        thread.start()

    def _stream_completion(self, assistant_message: dict) -> None:
        url = f"http://{self._host}:{self._port}/v1/chat/completions"
        model_name = _fetch_loaded_model() or "default"
        self._logger.info("Chat completion request: model=%s", model_name)
        tool_call_buffer: dict[int, dict[str, str]] = {}
        payload = {
            "model": model_name,
            "messages": self.messages,
            "stream": True,
        }
        if self._tool_schemas:
            payload["tools"] = self._tool_schemas
        data = json.dumps(payload).encode("utf-8")
        try:
            for attempt in range(2):
                request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
                start_time = time.monotonic()
                try:
                    with urllib.request.urlopen(request, timeout=60) as response:
                        content_type = response.headers.get("Content-Type", "")
                        if "text/event-stream" not in content_type:
                            body = response.read().decode("utf-8")
                            self._logger.info(
                                "Chat response non-streaming (Content-Type=%s, bytes=%d)",
                                content_type,
                                len(body),
                            )
                            try:
                                payload = json.loads(body) if body else {}
                            except json.JSONDecodeError:
                                self._logger.warning("Chat response non-streaming JSON parse failed")
                                payload = {}
                            message_text = self._extract_message_content(payload)
                            tool_calls = self._extract_tool_calls(payload)
                            if tool_calls:
                                self._logger.info("Chat response tool calls: %d", len(tool_calls))
                                with self._lock:
                                    assistant_message["tool_calls"] = self._build_tool_calls_payload(tool_calls)
                                self._handle_tool_calls(tool_calls)
                            if message_text:
                                with self._lock:
                                    assistant_message["content"] += message_text
                                self._log_stream_delta(message_text)
                                self._emit_stream_chunk(message_text)
                            else:
                                snippet = body[:500] if body else ""
                                self._logger.warning(
                                    "Chat response non-streaming contained no message content: %s",
                                    snippet,
                                )
                            self._flush_stream_log()
                            self._emit_stream_end()
                            return
                        for raw_line in response:
                            line = raw_line.decode("utf-8").strip()
                            if not line or not line.startswith("data:"):
                                continue
                            chunk = line[5:].strip()
                            if chunk == "[DONE]":
                                break
                            try:
                                payload = json.loads(chunk)
                            except json.JSONDecodeError:
                                continue
                            self._accumulate_tool_calls(payload, tool_call_buffer)
                            delta = self._extract_delta(payload)
                            if not delta:
                                continue
                            with self._lock:
                                assistant_message["content"] += delta
                            self._log_stream_delta(delta)
                            self._emit_stream_chunk(delta)
                    self._flush_stream_log()
                    tool_calls = self._finalize_tool_calls(tool_call_buffer)
                    if tool_calls:
                        self._logger.info("Chat response tool calls: %d", len(tool_calls))
                        with self._lock:
                            assistant_message["tool_calls"] = self._build_tool_calls_payload(tool_calls)
                        self._handle_tool_calls(tool_calls)
                    else:
                        self._detect_tool_calls(assistant_message.get("content", ""))
                    self._emit_stream_end()
                    return
                except urllib.error.HTTPError as err:
                    body = err.read().decode("utf-8")
                    if err.code == 500 and "mmproj" in body.lower() and attempt == 0:
                        self._logger.info("Chat stream missing mmproj; restarting router and retrying")
                        _restart_router_with_preset()
                        try:
                            load_model(model_name)
                        except Exception:
                            pass
                        continue
                    self._logger.error("Chat stream failed: HTTP %s %s", err.code, body)
                    self._flush_stream_log()
                    return
                except Exception as exc:
                    elapsed = time.monotonic() - start_time
                    self._logger.error("Chat stream failed after %.1fs: %s", elapsed, exc)
                    self._flush_stream_log()
                    return
        finally:
            self._active_request = False
            if self._model_ready:
                self._set_availability("AVAILABLE")
            else:
                self._set_availability("BUSY")

    def _emit_stream_chunk(self, chunk: str) -> None:
        for callback in self._stream_callbacks:
            try:
                callback(chunk)
            except Exception:
                continue

    def _emit_stream_end(self) -> None:
        for callback in self._stream_end_callbacks:
            try:
                callback()
            except Exception:
                continue

    def get_tools_advertisement(self) -> tuple[str, list[tuple[str, str]]] | None:
        if not self._tool_schemas:
            if not self._mcp_loading:
                self._load_mcp_tools_from_settings_async()
            return None
        details: list[tuple[str, str]] = []
        settings = load_settings_fresh()
        general_preamble = settings.get("tool_preamble_general") or ""
        cards_preamble = settings.get("tool_preamble_cards") or ""
        if general_preamble:
            details.append(("tool_preamble_general", general_preamble))
        if cards_preamble and any(
            (schema.get("function") or {}).get("name", "").startswith(f"{INTERNAL_MCP_NAME}.")
            for schema in self._tool_schemas
            if isinstance(schema, dict)
        ):
            details.append(("tool_preamble_cards", cards_preamble))
        for server_name, instructions in self._tool_server_instructions.items():
            if instructions:
                details.append((f"{server_name}.instructions", instructions))
        for schema in self._tool_schemas:
            function = schema.get("function") if isinstance(schema, dict) else None
            if not isinstance(function, dict):
                continue
            name = function.get("name") or ""
            description = function.get("description") or ""
            if name:
                details.append((name, description))
        content = f"Tools Advertisement ({len(details)} tools)"
        return content, details

    def _log_stream_delta(self, delta: str) -> None:
        if not delta:
            return
        self._stream_log_buffer += delta
        while True:
            newline_index = self._stream_log_buffer.find("\n")
            if newline_index != -1:
                line = self._stream_log_buffer[:newline_index]
                self._stream_log_buffer = self._stream_log_buffer[newline_index + 1 :]
                if line:
                    self._logger.info("Assistant: %s", line)
                continue
            if len(self._stream_log_buffer) >= 80:
                chunk = self._stream_log_buffer[:80]
                self._stream_log_buffer = self._stream_log_buffer[80:]
                self._logger.info("Assistant: %s", chunk)
                continue
            break

    def _flush_stream_log(self) -> None:
        if self._stream_log_buffer:
            self._logger.info("Assistant: %s", self._stream_log_buffer)
            self._stream_log_buffer = ""

    def _detect_tool_calls(self, text: str) -> None:
        if not text:
            return
        try:
            calls = self._adapter.parse_tool_calls(text)
        except Exception:
            return
        if not calls:
            return
        for call in calls:
            self._logger.info("Tool call detected: %s", call.name)
            for callback in self._tool_call_callbacks:
                try:
                    callback(call)
                except Exception:
                    continue
        self._handle_tool_calls(calls)

    def _handle_tool_calls(self, calls: list[ToolCall]) -> None:
        executor = self._tool_executor
        if executor is None:
            return
        for index, call in enumerate(calls, start=1):
            for callback in self._tool_call_callbacks:
                try:
                    callback(call)
                except Exception:
                    continue
            try:
                result = executor.execute(call)
            except Exception as exc:
                result = {"error": str(exc)}
            if call.name == f"{INTERNAL_MCP_NAME}.CreateCard":
                guid = None
                if isinstance(result, str):
                    guid = result
                elif isinstance(result, dict):
                    guid = result.get("guid") or result.get("GUID")
                if guid and guid not in self._internal_card_guids:
                    self._internal_card_guids.add(guid)
                    self._set_internal_drawcard_enabled(True)
            for callback in self._tool_result_callbacks:
                try:
                    callback(call, result)
                except Exception:
                    continue
            with self._lock:
                self._messages.append(
                    {
                        "role": "tool",
                        "content": json.dumps(result),
                        "tool_call_id": f"call_{index}",
                    }
                )
        followup_message = {"role": "assistant", "content": ""}
        with self._lock:
            self._messages.append(followup_message)
        for callback in self._followup_callbacks:
            try:
                callback()
            except Exception:
                continue
        self._stream_completion(followup_message)

    def _load_mcp_tools_from_settings(self, timeout: float | None = 3.0) -> None:
        with self._mcp_load_lock:
            if self._mcp_loading:
                return
            self._mcp_loading = True
        settings = load_settings_fresh()
        mcp_settings = settings.get("mcp_settings") or {}
        servers = mcp_settings.get("servers") or {}

        registry = ToolRegistry()
        schemas: list[dict] = []
        tool_map: dict[str, tuple[MCPClientManager, str]] = {}
        instructions_map: dict[str, str] = {}

        default_mcp_folder = Path(__file__).parent.parent / "MCP_Local"
        folder = Path(mcp_settings.get("folder") or default_mcp_folder)
        for server_name, state in servers.items():
            if not state.get("enabled", False):
                continue
            transport = state.get("transport", "stdio")
            transport = self._coerce_transport(server_name, transport, folder)
            manager: MCPClientManager | None = None

            if transport == "stdio":
                script_path = folder / f"{server_name}.py"
                if not script_path.exists():
                    continue
                manager = MCPClientManager(str(script_path))
            else:
                url = (state.get("url") or "").rstrip("/")
                port = str(state.get("port") or "").strip()
                if not url:
                    continue
                server_url = f"{url}:{port}/mcp" if port else f"{url}/mcp"
                manager = MCPClientManager(server_url)

            try:
                tools = manager.list_tools(timeout=timeout)
                instructions = manager.get_instructions(timeout=timeout)
                if instructions:
                    instructions_map[server_name] = instructions
            except Exception as exc:
                self._logger.warning("Failed to load MCP tools from %s: %s", server_name, exc)
                continue

            for tool in tools:
                base_name = getattr(tool, "name", None) or tool.get("name")
                description = getattr(tool, "description", None) or tool.get("description") or ""
                input_schema = (
                    getattr(tool, "inputSchema", None)
                    or tool.get("inputSchema")
                    or tool.get("parameters")
                    or {"type": "object", "properties": {}}
                )
                if not base_name:
                    continue
                tool_name = f"{server_name}.{base_name}"
                enabled = self._is_tool_enabled(tool_name, servers)
                schema = {
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": description,
                        "parameters": input_schema,
                    },
                }
                registry.register(ToolDefinition(name=tool_name, schema=schema, source="mcp", enabled=enabled))
                tool_map[tool_name] = (manager, base_name)
                if enabled:
                    schemas.append(schema)

        internal_url = f"http://{INTERNAL_MCP_HOST}:{INTERNAL_MCP_PORT}/mcp"
        built_in = settings.get("built_in_mcps", {})
        if isinstance(built_in, dict):
            internal_state = built_in.get(INTERNAL_MCP_NAME)
            if internal_state is None:
                internal_state = built_in.get("svg_card", {})
        else:
            internal_state = {}
        internal_enabled = bool(internal_state.get("enabled", True))
        self._internal_tools_enabled = internal_enabled
        internal_manager: MCPClientManager | None = None
        internal_tools: list = []
        if internal_enabled:
            try:
                internal_manager = MCPClientManager(internal_url)
                internal_tools = internal_manager.list_tools(timeout=timeout)
                instructions = internal_manager.get_instructions(timeout=timeout)
                if instructions:
                    instructions_map[INTERNAL_MCP_NAME] = instructions
            except Exception as exc:
                self._logger.warning("Failed to load internal MCP tools: %s", exc)
                internal_tools = []

        for tool in internal_tools:
            base_name = getattr(tool, "name", None) or tool.get("name")
            description = getattr(tool, "description", None) or tool.get("description") or ""
            input_schema = (
                getattr(tool, "inputSchema", None)
                or tool.get("inputSchema")
                or tool.get("parameters")
                or {"type": "object", "properties": {}}
            )
            if not base_name:
                continue
            tool_name = f"{INTERNAL_MCP_NAME}.{base_name}"
            schema = {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": description,
                    "parameters": input_schema,
                },
            }
            registry.register(
                ToolDefinition(
                    name=tool_name,
                    schema=schema,
                    source="internal",
                    enabled=internal_enabled,
                )
            )
            if internal_manager is None:
                continue
            tool_map[tool_name] = (internal_manager, base_name)
            if internal_enabled:
                schemas.append(schema)

        self._mcp_manager = None
        self._tool_registry = registry
        self._tool_schemas = schemas
        self._mcp_tool_map = tool_map
        self._tool_server_instructions = instructions_map
        self._tool_executor = ToolExecutor(registry, mcp_tool_map=tool_map)
        self._set_internal_drawcard_enabled(bool(self._internal_card_guids))
        self._logger.info("Loaded MCP tools from settings: %d", len(self._tool_schemas))
        with self._mcp_load_lock:
            self._mcp_loading = False

    def _load_mcp_tools_from_settings_async(self) -> None:
        thread = threading.Thread(target=self._load_mcp_tools_from_settings, daemon=True)
        thread.start()

    def _is_tool_enabled(self, tool_name: str, servers: dict) -> bool:
        server_name = None
        method_name = tool_name
        if "." in tool_name:
            server_name, method_name = tool_name.split(".", 1)
        elif "_" in tool_name:
            prefix, remainder = tool_name.split("_", 1)
            if prefix in servers:
                server_name, method_name = prefix, remainder
        if server_name and server_name in servers:
            methods = servers.get(server_name, {}).get("methods", {})
            if methods:
                return bool(methods.get(method_name, False))
        return True

    def _coerce_transport(self, server_name: str, transport: str, folder: Path) -> str:
        lower_name = server_name.lower()
        if lower_name.endswith("_http") and transport != "http":
            return "http"
        if lower_name.endswith("_stdio") and transport != "stdio":
            return "stdio"
        script_path = folder / f"{server_name}.py"
        if transport == "stdio" and script_path.exists() and self._is_http_script(script_path):
            return "http"
        return transport

    def _is_http_script(self, script_path: Path) -> bool:
        try:
            content = script_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return False
        return "transport=\"http\"" in content or "transport='http'" in content

    def _ensure_tool_system_message(self) -> None:
        if not self._tool_schemas:
            if self._tool_system_message is not None:
                with self._lock:
                    if self._tool_system_message in self._messages:
                        self._messages.remove(self._tool_system_message)
                self._tool_system_message = None
            return
        settings = load_settings_fresh()
        general_preamble = settings.get("tool_preamble_general") or ""
        cards_preamble = settings.get("tool_preamble_cards") or ""
        instruction_lines = []
        for server_name, instructions in self._tool_server_instructions.items():
            if instructions:
                instruction_lines.append(f"[{server_name}] {instructions}")
        combined_parts: list[str] = []
        if general_preamble:
            combined_parts.append(general_preamble)
        if cards_preamble and any(
            (schema.get("function") or {}).get("name", "").startswith(f"{INTERNAL_MCP_NAME}.")
            for schema in self._tool_schemas
            if isinstance(schema, dict)
        ):
            combined_parts.append(cards_preamble)
        combined_preamble = "\n\n".join(part for part in combined_parts if part)
        if instruction_lines:
            header = "MCP server instructions:"
            instructions_block = "\n".join([header, *instruction_lines])
            combined_preamble = (combined_preamble + "\n\n" if combined_preamble else "") + instructions_block
        rendered = self._adapter.render_tools(self._tool_schemas, combined_preamble)
        if not rendered:
            return
        if self._tool_system_message is None:
            system_message = {"role": "system", "content": rendered}
            with self._lock:
                self._messages.insert(0, system_message)
            self._tool_system_message = system_message
        else:
            with self._lock:
                self._tool_system_message["content"] = rendered
        self._tool_system_added = True

    def _set_internal_drawcard_enabled(self, enabled: bool) -> None:
        tool = self._tool_registry.get(f"{INTERNAL_MCP_NAME}.DrawCard")
        if tool is None:
            return
        if not self._internal_tools_enabled:
            if tool.enabled:
                tool.enabled = False
                self._tool_schemas = self._tool_registry.list_tools()
                self._ensure_tool_system_message()
            return
        if tool.enabled:
            return
        tool.enabled = True
        self._tool_schemas = self._tool_registry.list_tools()
        self._ensure_tool_system_message()

    def _get_chat_template(self) -> str | None:
        model_name = _fetch_loaded_model()
        settings = _load_settings()
        cache = settings.get("model_cache", {})
        entry = cache.get(model_name or "") if model_name else None
        if isinstance(entry, dict):
            return entry.get("chat_template")
        return None

    def _extract_delta(self, payload: dict) -> str:
        choices = payload.get("choices")
        if not choices:
            return ""
        choice = choices[0]
        delta = choice.get("delta") or {}
        content = delta.get("content")
        if content:
            return content
        message = choice.get("message") or {}
        return message.get("content") or ""

    def _extract_message_content(self, payload: dict) -> str:
        choices = payload.get("choices")
        if not choices:
            return ""
        choice = choices[0]
        message = choice.get("message") or {}
        content = message.get("content")
        if content:
            return content
        return self._extract_delta(payload)

    def _extract_tool_calls(self, payload: dict) -> list[ToolCall]:
        choices = payload.get("choices") or []
        if not choices:
            return []
        message = (choices[0].get("message") or {})
        return self._parse_tool_calls_list(message.get("tool_calls") or [])

    def _build_tool_calls_payload(self, calls: list[ToolCall]) -> list[dict[str, object]]:
        tool_calls: list[dict[str, object]] = []
        for index, call in enumerate(calls, start=1):
            arguments = call.arguments
            if not isinstance(arguments, str):
                try:
                    arguments = json.dumps(arguments)
                except Exception:
                    arguments = "{}"
            tool_calls.append(
                {
                    "id": f"call_{index}",
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": arguments,
                    },
                }
            )
        return tool_calls

    def _accumulate_tool_calls(self, payload: dict, buffer: dict[int, dict[str, str]]) -> None:
        choices = payload.get("choices") or []
        if not choices:
            return
        delta = choices[0].get("delta") or {}
        tool_calls = delta.get("tool_calls") or []
        for item in tool_calls:
            index = item.get("index", 0)
            function = item.get("function") or {}
            name = function.get("name")
            arguments = function.get("arguments") or ""
            entry = buffer.setdefault(index, {"name": "", "arguments": ""})
            if name:
                entry["name"] = name
            if arguments:
                entry["arguments"] += arguments

    def _finalize_tool_calls(self, buffer: dict[int, dict[str, str]]) -> list[ToolCall]:
        calls: list[ToolCall] = []
        for entry in buffer.values():
            name = entry.get("name") or ""
            raw_args = entry.get("arguments") or "{}"
            try:
                args = json.loads(raw_args)
            except json.JSONDecodeError:
                args = {}
            if name:
                calls.append(ToolCall(name=name, arguments=args, raw=raw_args))
        return calls

    def _parse_tool_calls_list(self, tool_calls: list[dict]) -> list[ToolCall]:
        calls: list[ToolCall] = []
        for item in tool_calls:
            function = item.get("function") or {}
            name = function.get("name") or ""
            raw_args = function.get("arguments") or "{}"
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError:
                args = {}
            if name:
                calls.append(ToolCall(name=name, arguments=args, raw=str(raw_args)))
        return calls

    def _build_content(self, text: str, image_paths: list[Path]) -> object:
        if not image_paths:
            return text

        parts: list[dict] = [{"type": "text", "text": text}]
        for path in image_paths:
            url = self._image_to_data_url(path)
            if not url:
                continue
            parts.append({"type": "image_url", "image_url": {"url": url}})
        return parts

    def _image_to_data_url(self, path: Path) -> Optional[str]:
        try:
            data = path.read_bytes()
        except Exception:
            return None
        mime_type, _ = mimetypes.guess_type(str(path))
        if not mime_type:
            mime_type = "image/png"
        encoded = base64.b64encode(data).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"

    def _on_model_state(self, state: str, _model_name: str | None) -> None:
        self._model_ready = state == "Ready"
        if self._active_request:
            self._set_availability("BUSY")
            return
        if self._model_ready:
            self._set_availability("AVAILABLE")
        else:
            self._set_availability("BUSY")

    def _set_availability(self, state: str) -> None:
        with self._availability_lock:
            if state == self._availability_state:
                return
            self._availability_state = state
        for callback in self._availability_callbacks:
            try:
                callback(state)
            except Exception:
                continue

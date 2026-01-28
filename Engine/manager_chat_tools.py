from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Callable

from Engine.manager_models_settings import load_settings_fresh
from Tools.mcp_client_manager import MCPClientManager
from Tools.tool_executor import ToolExecutor
from Tools.tool_protocol_base import ToolCall
from Tools.tool_registry import ToolDefinition, ToolRegistry
from constants import INTERNAL_MCP_HOST, INTERNAL_MCP_NAME, INTERNAL_MCP_PORT


class ChatToolManager:
    def __init__(
        self,
        logger,
        lock: threading.Lock,
        messages: list[dict],
        tool_call_callbacks: list[Callable[[ToolCall], None]],
        tool_result_callbacks: list[Callable[[ToolCall, object], None]],
        followup_callbacks: list[Callable[[], None]],
    ) -> None:
        self._logger = logger
        self._lock = lock
        self._messages = messages
        self._tool_call_callbacks = tool_call_callbacks
        self._tool_result_callbacks = tool_result_callbacks
        self._followup_callbacks = followup_callbacks
        self._tool_registry = ToolRegistry()
        self._tool_schemas: list[dict] = []
        self._tool_server_instructions: dict[str, str] = {}
        self._tool_system_message: dict | None = None
        self._tool_system_added = False
        self._internal_card_guids: set[str] = set()
        self._internal_tools_enabled = False
        self._mcp_manager: MCPClientManager | None = None
        self._tool_executor: ToolExecutor | None = None
        self._mcp_load_lock = threading.Lock()
        self._mcp_loading = False
        self._mcp_tool_map: dict[str, tuple[MCPClientManager, str]] = {}

    def is_loading(self) -> bool:
        return self._mcp_loading

    def get_tool_schemas(self) -> list[dict]:
        return list(self._tool_schemas)

    def get_user_tool_names(self) -> list[str]:
        if not self._tool_schemas and not self._mcp_loading:
            self.load_mcp_tools_from_settings_async()
        tool_names: list[str] = []
        for schema in self._tool_schemas:
            function = schema.get("function") if isinstance(schema, dict) else None
            if isinstance(function, dict):
                name = function.get("name")
                if name:
                    tool_names.append(str(name))
        return tool_names

    def get_tools_advertisement(self) -> tuple[str, list[tuple[str, str]]] | None:
        if not self._tool_schemas:
            if not self._mcp_loading:
                self.load_mcp_tools_from_settings_async()
            return None
        details: list[tuple[str, str]] = []
        settings = load_settings_fresh()
        general_preamble = settings.get("tool_preamble_general") or ""
        if general_preamble:
            details.append(("tool_preamble_general", general_preamble))
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

    def clear_internal_cards(self) -> None:
        self._internal_card_guids.clear()
        self._set_internal_drawcard_enabled(False)

    def ensure_tool_system_message(self, adapter) -> None:
        if not self._tool_schemas:
            if self._tool_system_message is not None:
                with self._lock:
                    if self._tool_system_message in self._messages:
                        self._messages.remove(self._tool_system_message)
                self._tool_system_message = None
            return
        settings = load_settings_fresh()
        general_preamble = settings.get("tool_preamble_general") or ""
        instruction_lines = []
        for server_name, instructions in self._tool_server_instructions.items():
            if instructions:
                instruction_lines.append(f"[{server_name}] {instructions}")
        combined_parts: list[str] = []
        if general_preamble:
            combined_parts.append(general_preamble)
        combined_preamble = "\n\n".join(part for part in combined_parts if part)
        if instruction_lines:
            header = "MCP server instructions:"
            instructions_block = "\n".join([header, *instruction_lines])
            combined_preamble = (combined_preamble + "\n\n" if combined_preamble else "") + instructions_block
        rendered = adapter.render_tools(self._tool_schemas, combined_preamble)
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

    def detect_tool_calls(self, text: str, adapter, stream_completion: Callable[[dict], None]) -> None:
        if not text:
            return
        try:
            calls = adapter.parse_tool_calls(text)
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
        self.handle_tool_calls(calls, stream_completion)

    def handle_tool_calls(self, calls: list[ToolCall], stream_completion: Callable[[dict], None]) -> None:
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
            if call.name.startswith(f"{INTERNAL_MCP_NAME}.") and call.name.endswith(".CreateCard"):
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
        stream_completion(followup_message)

    def load_mcp_tools_from_settings_async(self) -> None:
        thread = threading.Thread(target=self._load_mcp_tools_from_settings, daemon=True)
        thread.start()

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
        if not isinstance(built_in, dict):
            built_in = {}

        internal_state = built_in.get(INTERNAL_MCP_NAME, {})
        internal_master_enabled = bool(internal_state.get("enabled", True))
        self._internal_tools_enabled = internal_master_enabled
        internal_manager: MCPClientManager | None = None
        internal_tools: list = []
        if internal_master_enabled:
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
            if "." in base_name:
                mcp_name = base_name.split(".", 1)[0]
            else:
                mcp_name = INTERNAL_MCP_NAME
            module_state = built_in.get(mcp_name)
            if module_state is None and mcp_name == "mcp_card_svg":
                module_state = built_in.get("card_svg") or built_in.get("svg_card")
            module_enabled = bool(module_state.get("enabled", True)) if isinstance(module_state, dict) else True
            internal_enabled = internal_master_enabled and module_enabled
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

    def _set_internal_drawcard_enabled(self, enabled: bool) -> None:
        if self._tool_registry is None:
            return
        changed = False
        for tool in self._tool_registry.list_definitions():
            name = tool.name
            if not name.startswith(f"{INTERNAL_MCP_NAME}.") or not name.endswith(".DrawCard"):
                continue
            if not self._internal_tools_enabled:
                if tool.enabled:
                    tool.enabled = False
                    changed = True
                continue
            if tool.enabled == enabled:
                continue
            tool.enabled = enabled
            changed = True
        if changed:
            self._tool_schemas = self._tool_registry.list_tools()
            if self._tool_system_message is not None:
                self._tool_system_added = False

import logging
import json
from typing import Optional, Dict, Any, List
from pathlib import Path

from PyQt6 import QtCore, QtWidgets

logger = logging.getLogger(__name__)


class McpInfoPanel(QtWidgets.QFrame):
    """MCP info and test harness panel.

    UI:
    - Header row: MCP server name + transport details (stdio command/args or HTTP URL)
    - Body: Left (30%) list of tool methods fetched asynchronously
             Right (70%) dynamic parameter inputs based on selected tool schema
    - Footer: Call button; emits a request signal to trigger execution and display bubbles

    Signals:
    - tool_call_requested(name: str, args: dict, server: dict)
    """

    tool_call_requested = QtCore.pyqtSignal(str, dict, dict)

    def __init__(self, settings: Optional[dict] = None, parent: Optional[QtWidgets.QWidget] = None, server: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(parent)
        self.setObjectName("McpInfoPanel")
        self.settings = settings or {}
        # Allow shrinking to any size
        self.setMinimumWidth(0)
        # Use fixed server if provided; else load from settings list
        if server:
            self.mcp_servers: List[Dict[str, Any]] = [server]
            self.current_server: Dict[str, Any] = server
        else:
            self.mcp_servers: List[Dict[str, Any]] = self.settings.get("mcp_servers", []) or []
            self.current_server: Dict[str, Any] = self.mcp_servers[0] if self.mcp_servers else {}
        self.tools: List[Dict[str, Any]] = []
        self.selected_tool: Optional[Dict[str, Any]] = None
        self.param_inputs: Dict[str, QtWidgets.QLineEdit] = {}

        self._build_ui()
        QtCore.QTimer.singleShot(0, self._fetch_tools_async)

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Header row: server selector + transport details
        header = QtWidgets.QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        self.server_combo = None
        self.server_label = QtWidgets.QLabel()
        self.server_label.setText(self._format_server_label(self.current_server))

        header.addWidget(QtWidgets.QLabel("MCP:"))
        # Hide selector for fixed server; otherwise show combo
        if len(self.mcp_servers) > 1:
            combo = QtWidgets.QComboBox()
            for srv in self.mcp_servers:
                name = srv.get("name", "unknown")
                combo.addItem(name, userData=srv)
            combo.currentIndexChanged.connect(self._on_server_changed)
            self.server_combo = combo
            header.addWidget(combo)
        header.addStretch(1)
        header.addWidget(self.server_label)

        # Body split: left tools list, right params
        body = QtWidgets.QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(10)

        # Left: tools list
        left_box = QtWidgets.QVBoxLayout()
        left_box.setContentsMargins(0, 0, 0, 0)
        left_box.setSpacing(4)

        self.tools_list = QtWidgets.QListWidget()
        self.tools_list.setMaximumWidth(200)  # Prefer 200 but allow shrinking
        self.tools_list.itemSelectionChanged.connect(self._on_tool_selected)
        left_box.addWidget(self.tools_list, 1)

        # Footer: Call button (below the list)
        self.call_btn = QtWidgets.QPushButton("Call")
        self.call_btn.setEnabled(False)
        self.call_btn.clicked.connect(self._on_call_clicked)
        left_box.addWidget(self.call_btn)

        # Right: dynamic parameters
        right_box = QtWidgets.QWidget()
        self.params_layout = QtWidgets.QFormLayout()
        self.params_layout.setContentsMargins(0, 0, 0, 0)
        self.params_layout.setSpacing(6)
        right_box.setLayout(self.params_layout)

        # Assemble body with 30%/70% distribution
        body.addLayout(left_box, 3)
        body.addWidget(right_box, 7)

        layout.addLayout(header)
        layout.addLayout(body)

        # Styling
        self.setStyleSheet(
            """
            #McpInfoPanel {
                background-color: #2f343b;
                border: 1px solid #888;
                border-radius: 4px;
            }
            QListWidget { background: #fff; }
            QLineEdit { background: #ffffff; }
            """
        )

        self.setLayout(layout)

    def _format_server_label(self, server: Dict[str, Any]) -> str:
        if not server:
            return "No MCP configured"
        name = server.get("name", "unknown")
        if "url" in server:
            return f"Transport: HTTP • {server.get('url')}"
        cmd = server.get("command", "")
        args = server.get("args", "")
        args_str = args if isinstance(args, str) else " ".join(args) if isinstance(args, list) else str(args)
        return f"Transport: stdio • {cmd} {args_str}".strip()

    def _on_server_changed(self, index: int) -> None:
        self.current_server = self.server_combo.itemData(index) or {}
        self.server_label.setText(self._format_server_label(self.current_server))
        self._clear_tools()
        self._fetch_tools_async()

    def _clear_tools(self) -> None:
        self.tools = []
        self.tools_list.clear()
        self._clear_params()
        self.call_btn.setEnabled(False)

    def _clear_params(self) -> None:
        # Remove old param rows
        while self.params_layout.rowCount() > 0:
            self.params_layout.removeRow(0)
        self.param_inputs.clear()

    def _on_tool_selected(self) -> None:
        items = self.tools_list.selectedItems()
        if not items:
            self.selected_tool = None
            self._clear_params()
            self.call_btn.setEnabled(False)
            return
        item = items[0]
        tool: Dict[str, Any] = item.data(QtCore.Qt.ItemDataRole.UserRole)
        self.selected_tool = tool
        self._build_param_inputs(tool)
        self.call_btn.setEnabled(True)

    def _build_param_inputs(self, tool: Dict[str, Any]) -> None:
        self._clear_params()
        # Tool schema may be under 'function.parameters' (OpenAI format) or 'inputSchema' (MCP)
        schema = None
        if tool.get("function"):
            schema = tool["function"].get("parameters")
        if not schema:
            schema = tool.get("inputSchema")
        props = {}
        required = []
        if isinstance(schema, dict):
            props = schema.get("properties", {}) or {}
            required = schema.get("required", []) or []
        for name, info in props.items():
            label_text = f"{name}"
            if name in required:
                label_text += " *"
            edit = QtWidgets.QLineEdit()
            edit.setPlaceholderText(info.get("description", ""))
            self.params_layout.addRow(QtWidgets.QLabel(label_text), edit)
            self.param_inputs[name] = edit

    def _on_call_clicked(self) -> None:
        if not self.selected_tool:
            return
        name = self.selected_tool.get("name") or (
            self.selected_tool.get("function", {}).get("name")
        )
        if not name:
            return
        args: Dict[str, Any] = {}
        for k, w in self.param_inputs.items():
            val = w.text().strip()
            if val:
                # Try JSON parse to support objects/arrays
                try:
                    args[k] = json.loads(val)
                except Exception:
                    args[k] = val
        # Emit signal to outer window to create bubbles and execute
        logger.info(f"[MCP Panel] Requesting tool call: {name}({args}) via {self.current_server.get('name')}")
        self.tool_call_requested.emit(name, args, self.current_server)

    def _fetch_tools_async(self) -> None:
        # Run fetch in a worker thread to avoid blocking UI
        if not self.current_server:
            # No servers configured; show placeholder error and return
            self._on_tools_error("No MCP server configured")
            return
        worker = _ToolsFetchWorker(self.current_server)
        worker.signals.completed.connect(self._on_tools_fetched)
        worker.signals.error.connect(self._on_tools_error)
        QtCore.QThreadPool.globalInstance().start(worker)

    def _on_tools_fetched(self, tools: List[Dict[str, Any]]) -> None:
        self.tools = tools or []
        self.tools_list.clear()
        for tool in self.tools:
            # Normalize display/name
            name = tool.get("name") or tool.get("function", {}).get("name") or "unknown"
            item = QtWidgets.QListWidgetItem(name)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, tool)
            self.tools_list.addItem(item)
        self.call_btn.setEnabled(bool(self.tools))
        logger.info(f"[MCP Panel] Loaded {len(self.tools)} tool(s) from server")

    def _on_tools_error(self, message: str) -> None:
        logger.error(f"[MCP Panel] Tool fetch error: {message}")
        self.tools_list.clear()
        self.tools_list.addItem(QtWidgets.QListWidgetItem(f"Error: {message}"))
        self.call_btn.setEnabled(False)


class _WorkerSignals(QtCore.QObject):
    completed = QtCore.pyqtSignal(list)
    error = QtCore.pyqtSignal(str)


class _ToolsFetchWorker(QtCore.QRunnable):
    def __init__(self, server: Dict[str, Any]):
        super().__init__()
        self.server = server or {}
        self.signals = _WorkerSignals()

    @QtCore.pyqtSlot()
    def run(self) -> None:
        try:
            tools = self._fetch()
            self.signals.completed.emit(tools or [])
        except Exception as e:
            self.signals.error.emit(str(e))

    def _fetch(self) -> List[Dict[str, Any]]:
        # Check if tools were provided directly (builtin MCP)
        if "_builtin_tools" in self.server:
            logger.debug(f"Using provided tools for {self.server.get('name')}")
            return self.server.get("_builtin_tools", [])
        
        # Support stdio (command/args) and HTTP (url)
        if "url" in self.server:
            import asyncio
            from fastmcp import Client
            
            url = self.server.get("url")
            
            # For HTTP servers, add retry logic with exponential backoff
            max_retries = 5
            retry_delay = 0.5
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    async def get_tools_async():
                        """Query MCP server for available tools using FastMCP Client."""
                        client = Client(url)
                        async with client:
                            # List available tools
                            response = await client.list_tools()
                            tools = [
                                {
                                    "name": tool.name,
                                    "description": tool.description or "",
                                    "inputSchema": tool.inputSchema or {}
                                }
                                for tool in response.tools
                            ]
                            return tools
                    
                    # Run async function
                    tools = asyncio.run(get_tools_async())
                    if tools:
                        logger.debug(f"Fetched {len(tools)} tools from {url} via FastMCP Client")
                        return tools
                    
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        logger.debug(f"MCP fetch attempt {attempt + 1}/{max_retries} failed, retrying in {retry_delay}s: {e}")
                        import time
                        time.sleep(retry_delay)
                        retry_delay *= 1.5
                    else:
                        logger.error(f"MCP fetch failed after {max_retries} attempts: {last_error}")
            
            raise RuntimeError(f"HTTP MCP tools fetch failed: {last_error}")
        # stdio via mcp.client
        command = self.server.get("command")
        args = self.server.get("args")
        if not command:
            raise RuntimeError("No MCP server command provided")
        try:
            import asyncio
            from mcp.client.session import ClientSession
            from mcp.client.stdio import stdio_client, StdioServerParameters

            async def get_tools():
                server_params = StdioServerParameters(
                    command=command,
                    args=args if isinstance(args, list) else [args] if isinstance(args, str) else [],
                    cwd=Path.cwd(),
                )
                async with stdio_client(server_params) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        tools_response = await session.list_tools()
                        # Convert to OpenAI-like format for easier UI consumption
                        tools: List[Dict[str, Any]] = []
                        for t in tools_response.tools:
                            tools.append({
                                "name": getattr(t, "name", "unknown"),
                                "description": getattr(t, "description", ""),
                                "inputSchema": getattr(t, "inputSchema", {})
                            })
                        return tools

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(get_tools())
            loop.close()
            return result or []
        except Exception as e:
            raise RuntimeError(f"Stdio MCP tools fetch failed: {e}")

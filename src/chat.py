import os
import sys
import logging
import subprocess
import requests
import time
import yaml
import argparse
import json
import re
import base64
import mimetypes
from pathlib import Path
from typing import Optional
from datetime import datetime
from PyQt6.QtGui import QPixmap
from chatllama_MODELS import (
    LoadResult,
    LlamaModelLoader,
    ModelValidator,
    ModelCapabilities,
    ModelLoadWorker,
)
from chatllama_mcp_server import McpToolManager

try:
    import gguf
except ImportError:
    gguf = None

# Define project paths
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
LOGS_DIR = PROJECT_ROOT / "logs"
TEST_MCP_DIR = PROJECT_ROOT / "test_mcp"

# Set up logging with both main log and session-specific logs
LOGS_DIR.mkdir(exist_ok=True)

# Main application log (cumulative)
main_log_file = PROJECT_ROOT / "chatllama.log"

# Session-specific log (one per run with timestamp)
session_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
session_log_file = LOGS_DIR / f"session_{session_timestamp}.log"
session_screenshot_file = LOGS_DIR / f"session_{session_timestamp}.png"

log_format = "%(asctime)s - %(levelname)s - %(message)s"

# Configure UTF-8 console output for Unicode support (emojis)
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add TRACE level (below DEBUG) for protocol-level traffic
TRACE = 5
logging.addLevelName(TRACE, 'TRACE')

def trace(self, message, *args, **kwargs):
    if self.isEnabledFor(TRACE):
        self._log(TRACE, message, args, **kwargs)

logging.Logger.trace = trace

logging.basicConfig(
    level=logging.DEBUG,
    format=log_format,
    handlers=[
        logging.FileHandler(main_log_file, encoding='utf-8'),  # Main log file
        logging.FileHandler(session_log_file, encoding='utf-8'),  # Session-specific log
        logging.StreamHandler(sys.stdout)  # Console output
    ]
)
logger = logging.getLogger(__name__)
logger.info("=" * 60)
logger.info(f"ChatLlama started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
logger.info(f"Session log: {session_log_file}")
logger.info("=" * 60)

# Load settings from config/settings.yml (also sets up environment)
from chatllama_MODELS import load_settings

settings_file = CONFIG_DIR / "settings.yml"
config = load_settings(settings_file)

# Extract configuration into module-level constants
MODELS_DIR = config["models_dir"]
DEFAULT_MODEL = config["default_model"]
LLAMA_SERVER_PORT = config["llama_server_port"]
GPU_OFFLOAD_LAYERS = config["gpu_offload_layers"]
MCP_SERVER_ENABLED = config["mcp_server_enabled"]
MCP_SERVER_COMMAND = config["mcp_server_command"]
TOOL_INTEGRATION_ENABLED = config["tool_integration_enabled"]
TOOL_PREAMBLE = config["tool_preamble"]
DEFAULT_CTX = config["default_ctx"]
settings = config["_raw_settings"]  # Keep raw settings for validator updates

# Set Qt plugin path for PyQt6 (must be before importing PyQt6)
# This is needed when running directly without conda activation
if "QT_PLUGIN_PATH" not in os.environ:
    conda_prefix = os.environ.get("CONDA_PREFIX")
    if not conda_prefix:
        # Try to detect conda env from sys.prefix
        conda_prefix = sys.prefix
    qt_plugin_path = os.path.join(conda_prefix, "Library", "lib", "qt6", "plugins")
    if os.path.exists(qt_plugin_path):
        os.environ["QT_PLUGIN_PATH"] = qt_plugin_path
        logger.debug(f"Set QT_PLUGIN_PATH to: {qt_plugin_path}")
    else:
        logger.warning(f"Qt plugins directory not found at: {qt_plugin_path}")
else:
    logger.debug(f"QT_PLUGIN_PATH already set to: {os.environ['QT_PLUGIN_PATH']}")

# WebEngine removed: no Chromium or QWebEngine configuration

from PyQt6 import QtCore, QtGui, QtWidgets
from chatllama_pane_settings import SettingsPanel
from chatllama_cpp import ChatLlamaCpp
# LM Studio support removed
from chatllama_pane_chat import PromptInput, ChatPanel
from chatllama_pane_cards import CardsPanel
from chatllama_pane_trace import TracePanel
from chatllama_pane_hwinfo import HardwareInfoPanel


class ChatWorker(QtCore.QObject):
    """Worker thread for handling chat completions without blocking the UI."""
    finished = QtCore.pyqtSignal()
    chunk_ready = QtCore.pyqtSignal(str)
    error_occurred = QtCore.pyqtSignal(str)
    usage_ready = QtCore.pyqtSignal(dict)  # Emits token usage stats

    def __init__(self, model, messages: list[dict], parent=None):
        super().__init__(parent)
        self.model = model
        self.messages = messages
        self.usage_stats = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def run(self) -> None:
        """Stream chat completion and emit chunks."""
        import time
        try:
            response_text = ""
            # Build the completion request (tools now injected via system prompt)
            completion_kwargs = {
                "messages": self.messages,
                "stream": True
            }
            
            # Start timing and log with visual marker
            start_time = time.time()
            first_token_time = None
            logger.info("[LLM] ►►► Starting completion: messages=%d", len(self.messages))
            
            chunk_count = 0
            last_log_length = 0
            for chunk in self.model.create_chat_completion(**completion_kwargs):
                chunk_count += 1
                
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    # Log first token latency
                    if first_token_time is None:
                        first_token_time = time.time()
                        latency = first_token_time - start_time
                        logger.info("[LLM] First token after %.2fs", latency)
                    
                    response_text += content
                    self.chunk_ready.emit(content)
                    
                    # Log every 10th chunk at DEBUG (optional detail)
                    if chunk_count % 10 == 0:
                        elapsed = time.time() - start_time
                        logger.debug("[LLM Stream] Chunk %d (+%.2fs): %s", chunk_count, elapsed, content[:30])
                
                # Capture usage stats from the final chunk
                usage = chunk.get("usage")
                if usage:
                    self.usage_stats = {
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0)
                    }
            
            # Calculate final metrics
            end_time = time.time()
            total_time = end_time - start_time
            chars_per_sec = len(response_text) / total_time if total_time > 0 else 0
            
            # Log completion with metrics and visual marker
            logger.info("[LLM] ◄◄◄ Complete: %d chars (%d chunks) in %.2fs @ %.1f chars/s", 
                       len(response_text), chunk_count, total_time, chars_per_sec)
            logger.info("[LLM] Response: %s", response_text[:200] + "..." if len(response_text) > 200 else response_text)
            
            # Emit usage stats if available
            if self.usage_stats["total_tokens"] > 0:
                self.usage_ready.emit(self.usage_stats)
            
            self.finished.emit()
        except Exception as e:
            logger.exception(f"ChatWorker error: {e}")
            self.error_occurred.emit(str(e))











class ChatWindow(QtWidgets.QMainWindow):
    def __init__(self, input_file: Optional[str] = None, selected_model: Optional[str] = None) -> None:
        super().__init__()
        self.setWindowTitle("ChatLlama")
        self.resize(1400, 900)
        self._settings_panel: Optional[SettingsPanel] = None
        self._chat_panel: Optional[ChatPanel] = None
        self._cards_panel: Optional[CardsPanel] = None
        self._trace_panel: Optional[TracePanel] = None
        self._main_splitter = None
        self._settings_collapsed = False
        self._cards_collapsed = False
        self._trace_collapsed = True  # Collapsed by default
        self._model = None
        self._messages: list[dict] = [
            {"role": "system", "content": "You are a helpful assistant."}
        ]
        self._chat_thread: Optional[QtCore.QThread] = None
        self._chat_worker: Optional[ChatWorker] = None
        self._use_llama_server = False
        self._mcp_server_process = None
        self._mcp_http_server = None
        self._mcp_tools = None  # Will be populated during chat
        self._mcp_manager = McpToolManager(
            command=MCP_SERVER_COMMAND,
            project_root=PROJECT_ROOT,
            tool_preamble=TOOL_PREAMBLE,
            tool_integration_enabled=TOOL_INTEGRATION_ENABLED,
            logger=logger,
        )
        self._load_thread: Optional[QtCore.QThread] = None
        self._load_worker: Optional[ModelLoadWorker] = None
        self._last_local_model: Optional[str] = None  # Store local model when switching modes
        self._cpp_handler: Optional[ChatLlamaCpp] = None
        self._lmstudio_handler: Optional[ChatLlamaLmStudio] = None
        
        # Automation mode for testing
        self.input_file = input_file
        self.automation_mode = input_file is not None
        self.pending_messages = []
        self.processing_message = False
        self.selected_model = selected_model  # Model specified via command line
        self.session_screenshot_file = session_screenshot_file  # Store screenshot path
        
        # Hardware info panel (GPU + token stats)
        self._hwinfo_panel: Optional[HardwareInfoPanel] = None
        
        # Model validator for discovery and capabilities
        self._model_validator = ModelValidator(
            models_dir=MODELS_DIR,
            settings_file=settings_file,
            settings=settings,
            model_capabilities_class=ModelCapabilities,
            parent_widget=self
        )
        self._model_loader = LlamaModelLoader(
            models_dir=MODELS_DIR,
            gpu_offload_layers=GPU_OFFLOAD_LAYERS,
            port=LLAMA_SERVER_PORT,
            llama_server_path=config["llama_server_path"],
        )
        logger.info(f"ModelValidator initialized with models_dir={MODELS_DIR}, last_model={settings.get('last_model')}")

        # Ensure the models drive is available (external drive guard)
        if not self._ensure_models_drive_available():
            return
        
        self._build_ui()
        # Discover available models and update the settings panel combo
        logger.info("Populating model list via ModelValidator")
        self._populate_models_with_capabilities()
        self._check_and_launch_mcp_server()
        self._init_model_on_startup()
        if self._hwinfo_panel:
            self._hwinfo_panel.start_monitoring()
        
        # Load automation messages if in automation mode
        if self.automation_mode:
            self.pending_messages = self._load_input_file(input_file)
            logger.info(f"Automation mode: loaded {len(self.pending_messages)} messages from {input_file}")

    def start_built_in_mcp_http(self, host: str = "127.0.0.1", port: int = 6821) -> None:
        """Start built-in MCP HTTP server in the background while UI runs."""
        try:
            from mcp_http_server import SVGLayoutStudioMCP
            rules_path = PROJECT_ROOT / "src" / "cards" / "svg_generation_rules.json"

            def ui_dispatch(svg: str) -> None:
                # Ensure execution on UI thread
                QtCore.QTimer.singleShot(0, lambda: self._cards_panel.display_svg(svg) if self._cards_panel else None)

            srv = SVGLayoutStudioMCP(ui_display_svg=ui_dispatch, rules_path=rules_path, host=host, port=port)
            ok = srv.start()
            if ok:
                self._mcp_http_server = srv
                logger.info(f"Built-in MCP HTTP server started on http://{host}:{port}")
                
                # Register with Settings panel so it appears in MCP list
                if self._settings_panel:
                    server_config = srv.get_server_config()
                    self._settings_panel.register_builtin_mcp(server_config)
                    logger.info(f"Built-in MCP registered in Settings panel: {server_config.get('name')}")
                
                # Re-fetch tools to merge built-in + external and update system prompt
                self._fetch_and_integrate_tools()
            else:
                logger.error("Failed to start built-in MCP HTTP server")
        except Exception as e:
            logger.error(f"start_built_in_mcp_http error: {e}")

    def _ensure_models_drive_available(self) -> bool:
        """Check that the models drive is mounted; warn and close if not."""
        try:
            drive_root = Path(MODELS_DIR.anchor or MODELS_DIR.drive or str(MODELS_DIR)).anchor
            drive_path = Path(drive_root) if drive_root else MODELS_DIR.drive
            drive_path = Path(drive_path) if drive_path else MODELS_DIR

            if drive_path and not Path(drive_path).exists():
                msg = (
                    f"The models drive appears to be unavailable: {drive_path}.\n\n"
                    f"Expected models directory: {MODELS_DIR}\n"
                    "Please connect or mount the external drive, then restart ChatLlama."
                )
                logger.error(msg)
                QtWidgets.QMessageBox.warning(self, "Models drive not available", msg)
                QtCore.QTimer.singleShot(0, self.close)
                return False

            # Drive is reachable; if the directory itself is missing, allow normal discovery
            return True
        except Exception as e:
            logger.error(f"Failed drive availability check: {e}")
            return True


    def _build_ui(self) -> None:
        central = QtWidgets.QWidget()
        central.setObjectName("Central")
        central.setStyleSheet(
            """
            QWidget#Toolbar { background: #353a40; color: #f5f5f5; }
            QWidget#Toolbar QLabel { color: #f5f5f5; font-size: 18px; font-weight: 600; }
            QWidget#SettingsPanel { background: #2d3035; color: #f5f5f5; }
            QWidget#ChatPanel { background: #30343a; color: #f5f5f5; }
            QWidget#CardsPanel { background: #2a2d32; color: #f5f5f5; }
            QSplitter::handle { background: #ffffff; }
            QPlainTextEdit, QTextEdit { border: 1px solid #ffffff; background: #2f3338; color: #f5f5f5; }
            QLabel { color: #f5f5f5; }
            """
        )

        root_layout = QtWidgets.QVBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Create hardware info panel early so toolbar can embed it
        if self._hwinfo_panel is None:
            self._hwinfo_panel = HardwareInfoPanel()

        toolbar = self._build_toolbar()
        self._main_splitter = self._build_main_splitter()
        self._apply_splitter_sizes()

        root_layout.addWidget(toolbar)
        root_layout.addWidget(self._main_splitter, 1)

        central.setLayout(root_layout)
        self.setCentralWidget(central)
        
        # Add status bar
        self.statusBar().showMessage("Ready")

    def _build_toolbar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setObjectName("Toolbar")
        bar.setFixedHeight(48)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(16, 0, 16, 0)

        title = QtWidgets.QLabel("ChatLlama")
        title_font = QtGui.QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)

        layout.addWidget(title)
        layout.addStretch(1)

        # Settings toggle button with blue background when active (set)
        toggle_btn = QtWidgets.QPushButton("☰")
        toggle_btn.setMaximumWidth(48)
        toggle_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        toggle_btn.setCheckable(True)
        toggle_btn.setChecked(True)  # Set by default (settings visible)
        self._settings_toggle_btn = toggle_btn  # Store reference
        toggle_btn.clicked.connect(self._toggle_settings)
        
        # Style the button with blue when checked, gray when unchecked
        toggle_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #4a7fd7;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 6px 10px;
                font-weight: 600;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #5a8fe7;
            }
            QPushButton:pressed {
                background-color: #3a6fc7;
            }
            QPushButton:!checked {
                background-color: #666666;
            }
            QPushButton:!checked:hover {
                background-color: #767676;
            }
            """
        )
        layout.addWidget(toggle_btn)

        # Cards toggle button with blue background when active (set)
        cards_btn = QtWidgets.QPushButton("🖼️")
        cards_btn.setMaximumWidth(48)
        cards_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        cards_btn.setCheckable(True)
        cards_btn.setChecked(True)  # Set by default (cards visible)
        self._cards_toggle_btn = cards_btn  # Store reference
        cards_btn.clicked.connect(self._toggle_cards)
        
        # Style the button with blue when checked, gray when unchecked
        cards_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #4a7fd7;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 6px 10px;
                font-weight: 600;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #5a8fe7;
            }
            QPushButton:pressed {
                background-color: #3a6fc7;
            }
            QPushButton:!checked {
                background-color: #666666;
            }
            QPushButton:!checked:hover {
                background-color: #767676;
            }
            """
        )
        layout.addWidget(cards_btn)

        # Trace toggle button (collapsed by default, so gray)
        trace_btn = QtWidgets.QPushButton("🔍")
        trace_btn.setMaximumWidth(48)
        trace_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        trace_btn.setCheckable(True)
        trace_btn.setChecked(False)  # Collapsed by default
        self._trace_toggle_btn = trace_btn  # Store reference
        trace_btn.clicked.connect(self._toggle_trace)
        
        # Style the button with blue when checked, gray when unchecked
        trace_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #4a7fd7;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 6px 10px;
                font-weight: 600;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #5a8fe7;
            }
            QPushButton:pressed {
                background-color: #3a6fc7;
            }
            QPushButton:!checked {
                background-color: #666666;
            }
            QPushButton:!checked:hover {
                background-color: #767676;
            }
            """
        )
        layout.addWidget(trace_btn)

        # Hardware info panel on toolbar (GPU + tokens)
        if self._hwinfo_panel:
            self._hwinfo_panel.setMaximumWidth(360)
            layout.addWidget(self._hwinfo_panel)

        bar.setLayout(layout)
        return bar

    def _build_main_splitter(self) -> QtWidgets.QSplitter:
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)

        # Create panel widgets
        self._settings_panel = SettingsPanel(default_ctx=DEFAULT_CTX, settings=settings)
        self._chat_panel = ChatPanel()
        self._cards_panel = CardsPanel()
        self._trace_panel = TracePanel()

        self._cpp_handler = ChatLlamaCpp(self)

        def apply_equal_policy(widget: QtWidgets.QWidget) -> None:
            policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Preferred)
            policy.setHorizontalStretch(1)
            widget.setMinimumWidth(0)
            widget.setSizePolicy(policy)

        for panel in (self._settings_panel, self._chat_panel, self._cards_panel, self._trace_panel):
            apply_equal_policy(panel)

        # Wrap each pane with a title label so captions are always visible
        def wrap_with_caption(title: str, widget: QtWidgets.QWidget) -> QtWidgets.QWidget:
            container = QtWidgets.QWidget()
            policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Preferred)
            policy.setHorizontalStretch(1)
            container.setMinimumWidth(0)
            container.setSizePolicy(policy)
            vbox = QtWidgets.QVBoxLayout()
            vbox.setContentsMargins(0, 0, 0, 0)
            vbox.setSpacing(0)

            toolbar = QtWidgets.QWidget()
            toolbar.setFixedHeight(48)
            hbox = QtWidgets.QHBoxLayout()
            hbox.setContentsMargins(12, 0, 12, 0)
            hbox.setSpacing(8)

            title_label = QtWidgets.QLabel(title)
            title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft)

            title_lower = title.lower()
            if title_lower == "settings":
                container.setStyleSheet("background-color: #30343a;")
                title_label.setStyleSheet("font-size: 15px; font-weight: 700; color: #f5f5f5;")
                toolbar.setStyleSheet("background-color: #3a3f46;")
            elif title_lower == "chat":
                container.setStyleSheet("background-color: #30343a;")
                title_label.setStyleSheet("font-size: 15px; font-weight: 700; color: #f5f5f5;")
                toolbar.setStyleSheet("background-color: #3a3f46;")
            elif title_lower == "trace":
                container.setStyleSheet("background-color: #1a1a1a;")
                title_label.setStyleSheet("font-size: 15px; font-weight: 700; color: #00ff00;")
                toolbar.setStyleSheet("background-color: #222222;")
            else:  # cards
                container.setStyleSheet("background-color: #2a2d32;")
                title_label.setStyleSheet("font-size: 15px; font-weight: 700; color: #f5f5f5;")
                toolbar.setStyleSheet("background-color: #33373d;")

            hbox.addWidget(title_label)
            # LM Studio toggle removed
            hbox.addStretch(1)
            toolbar.setLayout(hbox)

            vbox.addWidget(toolbar)
            vbox.addWidget(widget)
            container.setLayout(vbox)
            widget.setSizePolicy(policy)
            return container

        settings_wrap = wrap_with_caption("Settings", self._settings_panel)
        chat_wrap = wrap_with_caption("Chat", self._chat_panel)
        cards_wrap = wrap_with_caption("Cards", self._cards_panel)
        trace_wrap = wrap_with_caption("Trace", self._trace_panel)
        
        # Connect signals from settings subpanels
        if self._cpp_handler:
            self._settings_panel.cpp_panel.model_load_requested.connect(self._cpp_handler.load_model)
            self._settings_panel.cpp_panel.model_selection_changed.connect(self._cpp_handler.on_selection_changed)
        self._settings_panel.cpp_panel.ctx_changed.connect(self._on_ctx_changed)

        # LM Studio signal connections removed
        
        # Connect signals from chat panel
        self._chat_panel.send_requested.connect(lambda text: self._on_send_message())

        # Connect MCP test harness: trigger tool request + execution for all MCP panels
        if hasattr(self._settings_panel, "mcp_panels") and self._settings_panel.mcp_panels:
            for panel in self._settings_panel.mcp_panels:
                panel.tool_call_requested.connect(self._on_mcp_tool_call_requested)
        
        # LM Studio populate removed

        splitter.addWidget(settings_wrap)
        splitter.addWidget(chat_wrap)
        splitter.addWidget(cards_wrap)
        splitter.addWidget(trace_wrap)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 1)
        splitter.setStretchFactor(3, 1)

        return splitter

    def _on_mcp_tool_call_requested(self, tool_name: str, arguments: dict, server: dict) -> None:
        """Create tool request bubble and execute call via selected MCP server.

        Shows a TOOL REQUEST bubble, executes the tool, and appends a
        TOOL RESPONSE bubble with the formatted result.
        """
        try:
            # Add tool request bubble
            if self._chat_panel:
                self._chat_panel._create_message_bubble(
                    text="",
                    message_type="tool_request",
                    tool_request={"name": tool_name, "arguments": arguments},
                )

            # Execute tool via selected server
            result_text = self._execute_tool_on_server(server, tool_name, arguments)
            if not result_text:
                result_text = f"[TOOL_RESULT]\nError: Tool execution failed for {tool_name}\n[END_TOOL_RESULT]"

            # Add tool response bubble
            if self._chat_panel:
                self._chat_panel._create_message_bubble(
                    text="",
                    message_type="tool_response",
                    tool_response={"name": tool_name, "result": result_text},
                )
        except Exception as e:
            logger.error(f"MCP panel tool call handler error: {e}")

    def _execute_tool_on_server(self, server: dict, tool_name: str, arguments: dict) -> Optional[str]:
        """Execute a tool using either stdio MCP or HTTP MCP server entry.

        Returns formatted result text (wrapped in [TOOL_RESULT] tags) or None.
        """
        try:
            # HTTP transport (no fallbacks)
            if server and "url" in server:
                import requests
                base = str(server.get("url")).rstrip("/")
                # Try POST /call_tool then /tools/call
                for endpoint in ("/call_tool", "/tools/call"):
                    try:
                        resp = requests.post(
                            base + endpoint,
                            json={"name": tool_name, "arguments": arguments or {}},
                            timeout=10,
                        )
                        if resp.ok:
                            data = resp.json()
                            # Format generically
                            payload = json.dumps(data, indent=2)
                            return f"[TOOL_RESULT]\n{payload}\n[END_TOOL_RESULT]"
                    except Exception:
                        continue
                return None

            # stdio transport via mcp.client (no fallbacks)
            command = server.get("command") if server else None
            args = server.get("args") if server else None
            if not command:
                return None

            import asyncio
            from mcp.client.session import ClientSession
            from mcp.client.stdio import stdio_client, StdioServerParameters

            async def run_call():
                params = StdioServerParameters(
                    command=command,
                    args=args if isinstance(args, list) else [args] if isinstance(args, str) else [],
                    cwd=PROJECT_ROOT,
                )
                async with stdio_client(params) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        result = await session.call_tool(tool_name, arguments or {})
                        return result

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(run_call())
            loop.close()

            if not result:
                return None
            # Use existing formatter
            return self._format_tool_result(result, wrap_in_tags=True)
        except Exception as e:
            logger.error(f"Tool execution error on selected server: {e}")
            return None

    def _toggle_settings(self) -> None:
        self._toggle_panel(0, self._settings_panel, self._settings_toggle_btn, "_settings_collapsed")
    
    def _toggle_cards(self) -> None:
        self._toggle_panel(2, self._cards_panel, self._cards_toggle_btn, "_cards_collapsed")
    
    def _toggle_trace(self) -> None:
        self._toggle_panel(3, self._trace_panel, self._trace_toggle_btn, "_trace_collapsed")
    
    def _toggle_panel(self, index: int, panel: QtWidgets.QWidget, btn: QtWidgets.QPushButton, collapsed_attr: str) -> None:
        """Common method to toggle panel visibility and rebalance widths."""
        if not panel or not self._main_splitter or not btn:
            return

        collapsed = getattr(self, collapsed_attr, False)
        collapsed = not collapsed
        setattr(self, collapsed_attr, collapsed)

        panel.setVisible(not collapsed)
        btn.setChecked(not collapsed)

        self._apply_splitter_sizes()

    def _apply_splitter_sizes(self) -> None:
        """Ensure all visible columns share equal width; hidden ones are zero."""
        if not self._main_splitter:
            return

        flags = [
            not self._settings_collapsed,
            True,  # chat always visible
            not self._cards_collapsed,
            not self._trace_collapsed,
        ]

        sizes = [1000 if flag else 0 for flag in flags]
        self._main_splitter.setSizes(sizes)
    
    # Properties for backwards compatibility with old direct widget access
    @property
    def _model_combo(self):
        panel = getattr(self, "_settings_panel", None)
        if not panel:
            logger.warning("_model_combo: settings panel is not initialized")
            return None
        cpp = getattr(panel, "cpp_panel", None)
        if not cpp:
            logger.warning("_model_combo: cpp_panel is not available on settings panel")
            return None
        combo = getattr(cpp, "model_combo", None)
        if combo is None:
            logger.warning("_model_combo: model_combo is None on cpp_panel")
        return combo
    
    @property
    def _status_label(self):
        if self._settings_panel and self._settings_panel.cpp_panel:
            return self._settings_panel.cpp_panel.status_label
        return None
    
    @property
    def _ctx_spin(self):
        if self._settings_panel and self._settings_panel.cpp_panel:
            return self._settings_panel.cpp_panel.ctx_spin
        return None
    
    @property
    def _maker_label(self):
        if self._settings_panel and self._settings_panel.cpp_panel:
            return self._settings_panel.cpp_panel.maker_label
        return None
    
    @property
    def _history_widget(self):
        return self._chat_panel.history_widget if self._chat_panel else None
    
    @property
    def _prompt_input(self):
        return self._chat_panel.prompt_input if self._chat_panel else None
    
    @property
    def _send_btn(self):
        return self._chat_panel.send_btn if self._chat_panel else None

    @staticmethod
    def _discover_models_static() -> list[str]:
        """Static method to discover models (can be called without instance).
        
        DEPRECATED: Use ModelValidator.discover_models() instead.
        Kept for backward compatibility with handlers.
        """
        validator = ModelValidator(
            models_dir=MODELS_DIR,
            settings_file=settings_file,
            settings=settings,
            model_capabilities_class=ModelCapabilities,
            parent_widget=None
        )
        return validator.discover_models()

    def _discover_models(self) -> list[str]:
        """Discover models using the model validator."""
        return self._model_validator.discover_models()

    def _populate_models_with_capabilities(self) -> None:
        """Populate model combo box with model names and capability badges (fresh scan)."""
        combo = self._model_combo
        if combo is None:
            logger.warning("Model population skipped: model combo is None (settings panel not ready?)")
            return
        logger.info(f"Model population starting: opening discovery and scan dialogs; combo id={id(combo)}")
        self._model_validator.populate_models_with_capabilities(combo)
        logger.info("Model population completed")
    
    def _scan_models_with_progress(self, models: list[str], existing_cache: dict) -> dict:
        """DEPRECATED: Use ModelValidator.scan_models_with_progress() instead."""
        return self._model_validator.scan_models_with_progress(models, existing_cache)
    
    def _save_capabilities_cache(self, cache: dict) -> None:
        """DEPRECATED: Use ModelValidator.save_capabilities_cache() instead."""
        self._model_validator.save_capabilities_cache(cache)

    def _prune_missing_models(self, discovered_models: list[str], capabilities_cache: dict) -> dict:
        """DEPRECATED: no-op since caching has been removed."""
        return capabilities_cache
    
    def _measure_and_cache_vram(self, model_path: str) -> None:
        """Measure VRAM usage of loaded model and update cache.
        
        Args:
            model_path: Relative path to model (e.g., "author/model-name")
        """
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            
            if not gpus:
                logger.debug("No GPUs detected for VRAM measurement")
                return
            
            # Get current VRAM usage
            vram_mb = int(gpus[0].memoryUsed)
            logger.info(f"VRAM usage: {vram_mb} MB")
            
            # Update cache
            cache = settings.get("model_capabilities", {})
            if model_path not in cache:
                cache[model_path] = {}
            
            cache[model_path]["vram_mb"] = vram_mb
            
            # Save to settings
            self._save_capabilities_cache(cache)
            
        except ImportError:
            logger.debug("GPUtil not available for VRAM measurement (pip install gputil)")
        except Exception as e:
            logger.debug(f"Failed to measure VRAM: {e}")

    def _discover_models(self) -> list[str]:
        """Scan MODELS_DIR for model folders, searching through author subfolders."""
        return self._discover_models_static()

    def _on_load_model_clicked(self, model_path: Optional[str] = None) -> None:
        """Load the selected local model (async heat)."""
        if not model_path and self._model_combo:
            model_path = self._model_combo.currentData() or self._model_combo.currentText() or None
        if model_path:
            self._start_async_model_load(model_path)

    # LM Studio methods removed

    # LM Studio methods removed

    # LM Studio methods removed

    def _is_mcp_server_running(self) -> bool:
        """Check if MCP server process is running.
        
        For MCP servers, we just check if the process exists,
        since they use stdio/pipe communication, not HTTP.
        """
        if not self._mcp_server_process:
            return False
        # Check if process is still alive
        return self._mcp_server_process.poll() is None

    def _launch_mcp_server(self) -> bool:
        """Launch the MCP server in a background process.
        
        Uses the command specified in settings.yml.
        
        Returns:
            True if server process started, False otherwise.
        """
        try:
            logger.info(f"Launching MCP server: {MCP_SERVER_COMMAND}")
            
            cmd_parts = MCP_SERVER_COMMAND.split()
            # Make paths absolute from project root
            if cmd_parts[0].lower() == "python":
                # Keep 'python' as is, but resolve relative paths
                if len(cmd_parts) > 1:
                    script_path = Path(__file__).parent.parent / cmd_parts[1]
                    if script_path.exists():
                        cmd_parts[1] = str(script_path)
            
            # Don't capture stdio - MCP server needs access to stdin/stdout for stdio protocol
            self._mcp_server_process = subprocess.Popen(
                cmd_parts,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
            )
            
            # Wait briefly for process to start
            time.sleep(1)
            
            if self._is_mcp_server_running():
                logger.info("MCP server started successfully")
                return True
            else:
                logger.warning("MCP server process ended unexpectedly")
                return False
            
        except Exception as e:
            logger.error(f"Failed to launch MCP server: {e}")
            return False
            return False

    def _check_and_launch_mcp_server(self) -> None:
        """Check MCP server status and fetch tools.

        For stdio transport, stdio_client will spawn the process on demand,
        so we don't pre-launch here. We still trigger a tool fetch which will
        spin up the server as needed.
        """
        if not MCP_SERVER_ENABLED:
            return

        logger.info("MCP stdio mode: server will be spawned on demand")

        # Trigger tool fetch; stdio_client will spawn the server if needed
        self._fetch_and_integrate_tools()

    def _fetch_mcp_tools(self) -> Optional[list]:
        """Fetch available tools from the MCP server using MCP protocol.
        
        Caches tools after initial fetch to avoid losing tool metadata on subsequent
        fetches (which would create new MCP server processes with empty Tool objects).
        
        Uses the mcp client library to connect via stdio to the MCP server
        and call the standard tools/list endpoint.
        
        Returns:
            List of tool definitions from MCP server (or cached tools).
        """
        if not MCP_SERVER_ENABLED:
            logger.debug("MCP server not available for tool fetching")
            return None

        return self._mcp_manager.fetch_mcp_tools()

    def _build_tool_prompt(self, tools: list) -> str:
        """Build a system prompt section with tools using the preamble from settings.yml.
        
        Format matches LM Studio approach with [TOOL_REQUEST] and [END_TOOL_REQUEST] markers.
        Uses the tool_preamble from settings.yml with {tools_json} placeholder replacement.
        
        Args:
            tools: List of tool definitions (MCP ToolDescription objects)
            
        Returns:
            Formatted prompt section with tools and instructions
        """
        return self._mcp_manager.build_tool_prompt(tools)
    
    def _format_tools_for_prompt(self, tools: list) -> str:
        """DEPRECATED: Use _build_tool_prompt instead.
        
        Args:
            tools: List of tool definitions from MCP server
            
        Returns:
            Formatted string describing available tools
        """
        # Kept for backwards compatibility, delegates to _build_tool_prompt
        return self._build_tool_prompt(tools)

    def _convert_mcp_tools_to_openai_format(self, mcp_tools: list) -> list:
        """Convert MCP tool definitions to OpenAI-compatible format.
        
        MCP tools can come as either:
        - ToolDescription objects (from MCP client)
        - Dict format (from built-in MCPs or already converted)
        
        We convert them to the format expected by the LLM.
        
        Args:
            mcp_tools: List of MCP ToolDescription objects or dicts
            
        Returns:
            List of tools in OpenAI format
        """
        return self._mcp_manager.convert_mcp_tools_to_openai_format(mcp_tools)

    def _fetch_and_integrate_tools(self) -> None:
        """Fetch MCP tools and integrate them into the system prompt.
        
        This updates the system prompt to include available tools
        so the model knows about them and can suggest using them.
        DISABLED BY DEFAULT for clean chat experience.
        """
        if not TOOL_INTEGRATION_ENABLED:
            logger.debug("Tool integration disabled - clean chat mode")
            self._messages[0]["content"] = "You are a helpful assistant."
            return
        
        # Fetch external MCP tools
        tools = self._fetch_mcp_tools()
        
        # Merge with built-in MCP tools if available
        if self._mcp_http_server:
            try:
                builtin_tools = self._mcp_http_server.get_tools()
                if builtin_tools:
                    tools = self._mcp_manager.merge_builtin_tools(tools, builtin_tools)
            except Exception as e:
                logger.error(f"Failed to merge built-in MCP tools: {e}", exc_info=True)
        
        if not tools:
            logger.warning("No tools fetched from MCP servers; system prompt unchanged")
            self._messages[0]["content"] = "You are a helpful assistant."
            return
        
        openai_tools = self._convert_mcp_tools_to_openai_format(tools)
        if not openai_tools:
            logger.warning("Tool conversion failed; system prompt unchanged")
            self._messages[0]["content"] = "You are a helpful assistant."
            return

        # Cache tools for later use
        self._mcp_tools = tools
        
        # Log tool summary before building prompt
        logger.info(f"Final tool list for system prompt: {len(tools)} tools")
        for i, tool in enumerate(tools, 1):
            name = tool.get('name') if isinstance(tool, dict) else getattr(tool, 'name', 'unknown')
            desc = tool.get('description', 'no description') if isinstance(tool, dict) else getattr(tool, 'description', 'no description')
            logger.debug(f"  {i}. {name} - {str(desc)[:100]}")
        
        # Build tool prompt with {tools_json} replaced
        tool_prompt = self._build_tool_prompt(openai_tools)
        
        # Update system message to include tool information
        full_system_prompt = f"You are a helpful assistant.\n\n{tool_prompt}"
        self._messages[0]["content"] = full_system_prompt
        
        # Log full system prompt for verification
        logger.info(f"Updated system prompt with {len(tools)} tools")
        logger.debug(f"=== SYSTEM PROMPT START ===\n{full_system_prompt}\n=== SYSTEM PROMPT END ===")
        # Status label removed; no-op on connect

    def _parse_tool_request(self, text: str) -> Optional[tuple[str, dict]]:
        """Detect and parse LM Studio format tool calls from model output.
        
        Looks for [TOOL_REQUEST]...[END_TOOL_REQUEST] blocks containing JSON.
        Format: [TOOL_REQUEST]{\"name\": \"tool_name\", \"arguments\": {...}}[END_TOOL_REQUEST]
        
        Args:
            text: Model output text
            
        Returns:
            Tuple of (tool_name, arguments_dict) or None if no tool call found
        """
        # Find [TOOL_REQUEST] and [END_TOOL_REQUEST] markers
        start_marker = "[TOOL_REQUEST]"
        end_marker = "[END_TOOL_REQUEST]"
        
        start_idx = text.find(start_marker)
        end_idx = text.find(end_marker)
        
        if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
            logger.debug("No [TOOL_REQUEST] block found in model output")
            return None
        
        # Extract content between markers
        start_idx += len(start_marker)
        json_str = text[start_idx:end_idx].strip()
        logger.debug(f"Found TOOL_REQUEST JSON: {json_str[:100]}...")
        
        try:
            tool_call = json.loads(json_str)
            tool_name = tool_call.get("name")
            arguments = tool_call.get("arguments", {})
            
            if not tool_name:
                logger.warning("Tool call JSON missing 'name' field")
                return None
            
            logger.info(f"Parsed tool call: {tool_name} with arguments (complex args, {len(str(arguments))} chars)")
            return tool_name, arguments
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse TOOL_REQUEST JSON: {e}")
            logger.debug(f"JSON string was: {json_str}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error parsing tool request: {e}")
            return None

    def _format_tool_result(self, result, wrap_in_tags: bool = True) -> str:
        """Convert MCP CallToolResult into text format for LM Studio protocol.
        
        Args:
            result: MCP CallToolResult object
            wrap_in_tags: If True, wrap in [TOOL_RESULT]...[END_TOOL_RESULT] tags
            
        Returns:
            Formatted result text, optionally wrapped in tags
        """
        parts: list[str] = []

        try:
            content_items = getattr(result, "content", None)
            if content_items:
                for item in content_items:
                    if hasattr(item, "text"):
                        parts.append(item.text)
                    elif hasattr(item, "model_dump"):
                        parts.append(json.dumps(item.model_dump(), indent=2))
                    else:
                        parts.append(str(item))

            structured = getattr(result, "structuredContent", None)
            if structured and not parts:
                parts.append(json.dumps(structured, indent=2))
        except Exception as e:
            logger.debug(f"Failed to format tool content: {e}")

        if parts:
            text = "\n".join(parts)
            # Cap excessively long outputs to keep context manageable
            result_text = (text[:4000] + "\n... [truncated]") if len(text) > 4000 else text
        else:
            try:
                result_text = json.dumps(result.model_dump(), indent=2)
            except Exception:
                result_text = str(result)
        
        if wrap_in_tags:
            result_text = f"[TOOL_RESULT]\n{result_text}\n[END_TOOL_RESULT]"
        
        return result_text

    def _execute_tool_call(self, tool_name: str, arguments: dict) -> Optional[str]:
        """Execute a tool via MCP (HTTP or stdio) and return formatted result text.
        
        Tries built-in HTTP MCP first, then external stdio MCP.
        """
        import time
        import json
        
        if not MCP_SERVER_ENABLED:
            logger.warning("MCP server disabled; cannot execute tool")
            return None

        # Start tool execution block with visual marker
        start_time = time.time()
        logger.info("═" * 63)
        logger.info("[TOOL] ►►► Executing: %s", tool_name)
        logger.info("[TOOL]     Arguments: %s", json.dumps(arguments or {}, ensure_ascii=False))
        
        result = None
        method_used = None
        
        # Try built-in HTTP MCP server first
        if self._mcp_http_server:
            logger.debug("[TOOL] Trying built-in HTTP MCP")
            try:
                result = self._mcp_http_server.call_tool(tool_name, arguments or {})
                # Check if result is a successful response (not an error dict)
                if result and isinstance(result, dict) and result.get("status") == "error":
                    logger.debug("[TOOL] Built-in MCP returned error: %s", result.get('message'))
                    result = None  # Force fallback to stdio
                elif result:
                    method_used = "HTTP MCP :6821"
            except Exception as e:
                logger.debug("[TOOL] Built-in HTTP MCP failed: %s", e)
                result = None
        
        # Fall back to stdio MCP if HTTP didn't work or returned error
        if not result:
            logger.debug("[TOOL] Trying stdio MCP")
            try:
                import asyncio
                from mcp.client.session import ClientSession
                from mcp.client.stdio import stdio_client, StdioServerParameters

                cmd_parts = MCP_SERVER_COMMAND.split()

                async def run_call():
                    server_params = StdioServerParameters(
                        command=cmd_parts[0],
                        args=cmd_parts[1:] if len(cmd_parts) > 1 else [],
                        cwd=PROJECT_ROOT,
                    )
                    async with stdio_client(server_params) as (read_stream, write_stream):
                        async with ClientSession(read_stream, write_stream) as session:
                            await session.initialize()
                            result = await session.call_tool(tool_name, arguments or {})
                            return result

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(run_call())
                loop.close()
                
                if result:
                    method_used = "stdio MCP"
            except Exception as e:
                logger.error("[TOOL] Stdio MCP failed: %s", e)
                result = None

        # Log result with visual marker
        elapsed_ms = (time.time() - start_time) * 1000
        if result:
            logger.info("[TOOL] ◄◄◄ Success in %.0fms (via %s)", elapsed_ms, method_used)
            # Handle CallToolResult objects from MCP (convert to string/dict for logging)
            try:
                # Try to extract content from CallToolResult object
                if hasattr(result, 'content'):
                    # MCP CallToolResult has content attribute (list of TextContent/etc)
                    if isinstance(result.content, list) and result.content:
                        result_text = result.content[0].text if hasattr(result.content[0], 'text') else str(result.content[0])
                    else:
                        result_text = str(result.content)
                    result_str = result_text[:500] if isinstance(result_text, str) else str(result_text)[:500]
                else:
                    # Plain dict or other serializable object
                    result_str = json.dumps(result, ensure_ascii=False)
                
                if len(result_str) > 200:
                    logger.info("[TOOL]     Result: %s...", result_str[:200])
                else:
                    logger.info("[TOOL]     Result: %s", result_str)
            except Exception as e:
                logger.debug("[TOOL] Error formatting result: %s", e)
                logger.info("[TOOL]     Result: (unprintable object)")
        else:
            logger.warning("[TOOL] ◄◄◄ Failed in %.0fms (no result from any MCP source)", elapsed_ms)
        logger.info("═" * 63)

        if not result:
            return None

        try:
            return self._format_tool_result(result)
        except Exception as e:
            logger.warning(f"Could not format tool result for {tool_name}: {e}")
            try:
                # Try to get dict representation
                if hasattr(result, 'model_dump'):
                    return json.dumps(result.model_dump(), indent=2)
                else:
                    return str(result)
            except Exception:
                return str(result)

    def _handle_tool_request(self, tool_request: tuple[str, dict]) -> None:
        """Execute requested tool and continue the conversation with its output."""
        tool_name, args = tool_request
        logger.info(f"Detected tool request: {tool_name} with args {args}")
        self._append_to_history(f"Tool requested: {tool_name} {args}", message_type="tool")

        # Keep automation blocked while executing tool
        self.processing_message = True
        if self._send_btn:
            self._send_btn.setEnabled(False)
            self._send_btn.setText("Running tool...")

        logger.info(f"[TOOL] Starting execution of {tool_name}")
        tool_output = self._execute_tool_call(tool_name, args)
        logger.info(f"[TOOL] Execution complete for {tool_name}, output length: {len(tool_output) if tool_output else 0}")
        
        if not tool_output:
            self._append_to_history(f"Tool failed: {tool_name}", message_type="error")
            logger.error(f"Tool execution failed or returned empty result: {tool_name}")
            self.processing_message = False
            if self._send_btn:
                self._send_btn.setEnabled(True)
                self._send_btn.setText("Send (Ctrl+Enter)")
            if self.automation_mode and self.pending_messages:
                QtCore.QTimer.singleShot(1000, self._process_next_automation_message)
            return

        tool_message = f"Tool {tool_name} result:\n{tool_output}"
        # Append readable output to history with tool styling
        self._append_to_history(tool_message, message_type="tool")
        # Provide tool result to model as assistant content (avoids extra system messages)
        self._messages.append({"role": "assistant", "content": tool_message})
        logger.info(f"[TOOL] Added tool result to message history for {tool_name}")

        # Do NOT prune here - let _start_chat_completion handle pruning before next completion
        # This ensures tool results stay in context for the next turn
        # Do not immediately start another completion; avoid decoder issues
        # Re-enable send and continue automation if applicable
        self.processing_message = False
        if self._send_btn:
            self._send_btn.setEnabled(True)
            self._send_btn.setText("Send (Ctrl+Enter)")
        if self.automation_mode and self.pending_messages:
            QtCore.QTimer.singleShot(1000, self._process_next_automation_message)

    def _apply_load_result(self, result: LoadResult) -> None:
        model_rel = result.model_rel
        if not model_rel and result.model_file:
            try:
                path_obj = Path(result.model_file)
                if MODELS_DIR in path_obj.parents:
                    model_rel = str(path_obj.parent.relative_to(MODELS_DIR))
            except Exception:
                model_rel = None

        if not result.success:
            self._use_llama_server = False
            self._model = None
            self._set_status(result.message)
            if self._send_btn:
                self._send_btn.setEnabled(False)
                self._send_btn.setText("Select a model to begin")
            if self.automation_mode:
                # Stop automation cleanly when we cannot load the model
                self.pending_messages = []
                self.processing_message = False
                QtCore.QTimer.singleShot(0, self.close)
            return

        self._use_llama_server = result.used_llama_server
        self._model = result.model
        display_target = model_rel or (str(result.model_file) if result.model_file else None)

        if display_target:
            self._set_current_model(display_target)

        if model_rel:
            self._model_validator.set_last_model_name(model_rel)
            if not result.used_llama_server:
                self._measure_and_cache_vram(model_rel)

        self._set_status(result.message)
        if self._send_btn:
            self._send_btn.setEnabled(True)
            self._send_btn.setText("Send (Ctrl+Enter)")

    # Mode switching removed (LM Studio feature deprecated)

    # ----- Startup model heating -----
    def _init_model_on_startup(self) -> None:
        """Initialize model state: heat last model asynchronously, or disable chat until selection."""
        try:
            # Determine last model preference or CLI override
            last_model = self._model_validator.get_last_model_name()
            model_to_use = self.selected_model or last_model
            if model_to_use:
                # Select in combo if present
                if self._model_combo:
                    idx = -1
                    for i in range(self._model_combo.count()):
                        if self._model_combo.itemData(i) == model_to_use:
                            idx = i
                            break
                    if idx >= 0:
                        self._model_combo.setCurrentIndex(idx)
                # Disable chat and start async load/heat
                if self._send_btn:
                    self._send_btn.setEnabled(False)
                    self._send_btn.setText("Warming model...")
                self._start_async_model_load(model_to_use)
            else:
                # No last model; keep chat disabled until user selects and heats
                logger.info("No last_model in settings; waiting for user to select a model")
                if self._send_btn:
                    self._send_btn.setEnabled(False)
                    self._send_btn.setText("Select a model to begin")
                self._set_status("Select a model to begin")
        except Exception as e:
            logger.error(f"_init_model_on_startup error: {e}")

    def _start_async_model_load(self, model_path: str) -> None:
        """Begin asynchronous model load using LlamaModelLoader (handles full or relative paths)."""
        try:
            desired_ctx = self._ctx_spin.value() if self._ctx_spin else DEFAULT_CTX
            if self._send_btn:
                self._send_btn.setEnabled(False)
                self._send_btn.setText("Warming model...")

            # Clean up any existing worker/thread
            if self._load_thread:
                try:
                    self._load_thread.quit()
                    self._load_thread.wait(500)
                except Exception:
                    pass
                self._load_thread = None
                self._load_worker = None

            self._load_thread = QtCore.QThread()
            self._load_worker = ModelLoadWorker(self._model_loader, model_path, desired_ctx)
            self._load_worker.moveToThread(self._load_thread)
            self._load_thread.started.connect(self._load_worker.run)
            self._load_worker.finished.connect(self._on_model_loaded)
            self._load_worker.finished.connect(self._load_thread.quit)
            self._load_thread.finished.connect(self._load_thread.deleteLater)
            self._load_thread.start()
            self._set_status(f"Warming {Path(model_path).name}...")
        except Exception as e:
            logger.error(f"_start_async_model_load error: {e}")

    def _on_model_loaded(self, result: LoadResult) -> None:
        """Handle completion of async model loading (llama-server)."""
        try:
            self._apply_load_result(result)
        finally:
            try:
                if self._load_worker:
                    self._load_worker.deleteLater()
                if self._load_thread and self._load_thread.isRunning():
                    self._load_thread.quit()
                    self._load_thread.wait(2000)
            except Exception:
                pass
            self._load_thread = None
            self._load_worker = None

    def _load_lm_studio_models(self) -> None:
        """Fetch available models from LM Studio REST API."""
        try:
            lm_studio_port = settings.get("lm_studio_port", 11013)
            url = f"http://127.0.0.1:{lm_studio_port}/api/v0/models"
            
            logger.info(f"Fetching models from LM Studio: {url}")
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            models = data.get("data", [])
            
            if not models:
                logger.warning("No models returned from LM Studio API")
                lm_status = getattr(self._settings_panel.lmstudio_panel, "status_label", None) if self._settings_panel else None
                if lm_status:
                    lm_status.setText("No models available from LM Studio")
                return
            
            # Clear and populate combo box
            lm_combo = self._settings_panel.lmstudio_panel.model_combo if self._settings_panel else None
            lm_status = getattr(self._settings_panel.lmstudio_panel, "status_label", None) if self._settings_panel else None
            if lm_combo:
                lm_combo.clear()
                for model_info in models:
                    model_id = model_info.get("id", "unknown")
                    state = model_info.get("state", "unknown")
                    # Display model with state indicator
                    display_text = f"{model_id} ({state})"
                    lm_combo.addItem(display_text, userData=model_id)
                
                logger.info(f"Loaded {len(models)} models from LM Studio: {[m.get('id') for m in models]}")
                if lm_status:
                    lm_status.setText(f"Loaded {len(models)} models from LM Studio ✓")
                
                # Select first model
                if lm_combo.count() > 0:
                    lm_combo.setCurrentIndex(0)
        
        except Exception:
            pass
    
    # LM Studio feature removed
    
    # LM Studio feature removed
    
    def _set_current_model(self, model_name: str) -> None:
        """Update the display of the currently loaded model."""
        if self._settings_panel and self._settings_panel.cpp_panel:
            try:
                # Delegate to subpanel API to render combined header text
                self._settings_panel.cpp_panel.set_current_model(model_name)
                logger.debug(f"Updated current model display: {model_name}")
            except Exception:
                pass
    
    def _set_status(self, message: str) -> None:
        """Update the status label in the settings panel."""
        # Status row removed per spec; no-op
        return

    def _on_model_selection_changed(self, index: int) -> None:
        """Update context spin to default when model selection changes (no per-model overrides)."""
        if self._ctx_spin is None:
            return
        self._ctx_spin.setValue(DEFAULT_CTX)
        self._set_status(f"Model selected. Context: {DEFAULT_CTX} tokens")

    def _save_settings(self) -> None:
        """Persist current settings to YAML file (default ctx only)."""
        try:
            settings["default_ctx"] = DEFAULT_CTX
            with open(settings_file, 'w', encoding='utf-8') as f:
                yaml.safe_dump(settings, f, sort_keys=False, allow_unicode=True)
            logger.info("Settings saved (default_ctx updated)")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def _on_ctx_changed(self, value: int) -> None:
        """Persist new default context length (no per-model overrides)."""
        global DEFAULT_CTX
        DEFAULT_CTX = int(value)
        logger.info(f"Default context set: {value}")
        self._save_settings()

    def _on_send_message(self) -> None:
        """Handle send button click or Ctrl+Enter."""
        if not self._model:
            self._append_to_history("System: Model not loaded. Please load a model first.")
            return

        if not self._prompt_input:
            return

        user_input = self._prompt_input.toPlainText().strip()
        if not user_input:
            return

        # Collect any image attachments from the chat panel (up to 3)
        attachments: list[str] = []
        if self._chat_panel and hasattr(self._chat_panel, "get_attachments"):
            try:
                attachments = self._chat_panel.get_attachments()  # type: ignore[attr-defined]
            except Exception as e:
                logger.debug(f"Could not get attachments: {e}")

        # Log the message and attachments
        if attachments:
            logger.info(f"User message with {len(attachments)} image(s): {user_input}")
            logger.info(f"Attachments: {attachments}")
        else:
            logger.info(f"User message: {user_input}")

        # Add user message to history and messages (include thumbnails if any)
        self._append_to_history(user_input, message_type="user", image_paths=attachments)
        # Store attachments metadata alongside user message for future vision/tool use
        user_entry: dict = {"role": "user", "content": user_input}
        if attachments:
            user_entry["images"] = attachments
        self._messages.append(user_entry)
        self._prompt_input.clear()
        # Clear attachments after sending
        if self._chat_panel and hasattr(self._chat_panel, "clear_attachments"):
            try:
                self._chat_panel.clear_attachments()  # type: ignore[attr-defined]
            except Exception as e:
                logger.debug(f"Could not clear attachments: {e}")

        # Disable send button during response
        if self._send_btn:
            self._send_btn.setEnabled(False)
            self._send_btn.setText("Waiting for response...")

        # Start chat worker thread
        self._start_chat_completion()

    def _encode_image_to_data_url(self, path: str) -> Optional[str]:
        """Convert an image file into a data URL for llama-cpp vision input."""
        try:
            img_path = Path(path)
            if not img_path.exists():
                logger.warning(f"Attachment not found, skipping: {path}")
                return None

            mime_type, _ = mimetypes.guess_type(img_path.name)
            mime_type = mime_type or "image/png"

            with open(img_path, "rb") as f:
                b64_data = base64.b64encode(f.read()).decode("utf-8")

            return f"data:{mime_type};base64,{b64_data}"
        except Exception as e:
            logger.error(f"Failed to encode image {path}: {e}")
            return None

    def _prepare_messages_for_llama(self, messages: list[dict]) -> list[dict]:
        """Return messages formatted for llama-cpp, attaching images as data URLs when present."""
        prepared: list[dict] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            images = msg.get("images") or []

            if images:
                parts = [{"type": "text", "text": str(content)}]
                for img_path in images[:3]:
                    data_url = self._encode_image_to_data_url(img_path)
                    if data_url:
                        parts.append({"type": "image_url", "image_url": {"url": data_url}})
                prepared.append({"role": role, "content": parts})
            else:
                prepared.append({"role": role, "content": content})

        return prepared

    def _start_chat_completion(self) -> None:
        """Start the chat completion in a worker thread."""
        if not self._model:
            return
        
        # Prune conversation history if getting too long
        # Keep system message + recent N messages (default 20 pairs = 40 messages)
        MAX_MESSAGES = 41  # 1 system + 20 user/assistant pairs
        if len(self._messages) > MAX_MESSAGES:
            logger.warning(f"Message history ({len(self._messages)}) exceeds {MAX_MESSAGES}, pruning old messages")
            # Keep system message and most recent messages
            system_msg = self._messages[0] if self._messages[0].get("role") == "system" else None
            recent_messages = self._messages[-(MAX_MESSAGES - 1):]
            self._messages = ([system_msg] if system_msg else []) + recent_messages
            logger.info(f"Pruned history to {len(self._messages)} messages")

        # Fetch MCP tools (external only) and merge with built-in if available
        mcp_tools = self._fetch_mcp_tools()
        
        if self._mcp_http_server:
            try:
                builtin_tools = self._mcp_http_server.get_tools()
                mcp_tools = self._mcp_manager.merge_builtin_tools(mcp_tools, builtin_tools)
                if builtin_tools:
                    logger.debug(f"Merged {len(builtin_tools)} built-in tools for this chat completion")
            except Exception as e:
                logger.error(f"Failed to merge built-in tools in chat completion: {e}")
        
        if mcp_tools:
            logger.info(f"Chat completion: {len(mcp_tools)} tools available (including built-in)")
            for i, tool in enumerate(mcp_tools, 1):
                name = tool.get('name') if isinstance(tool, dict) else getattr(tool, 'name', 'unknown')
                desc = tool.get('description', '') if isinstance(tool, dict) else getattr(tool, 'description', '')
                logger.debug(f"  {i}. {name} - {str(desc)[:80]}")
            
            # Convert to OpenAI format
            tool_list = self._convert_mcp_tools_to_openai_format(mcp_tools)
            
            tool_prompt = self._build_tool_prompt(tool_list)
            if tool_prompt:
                # Inject into system message
                if self._messages[0]["role"] == "system":
                    self._messages[0]["content"] += tool_prompt
                    logger.debug(f"Injected tool prompt ({len(tool_prompt)} chars) into system message")
                else:
                    # Shouldn't happen, but handle gracefully
                    logger.warning("First message is not system message, skipping tool injection")
                logger.info(f"Injected {len(tool_list)} tools into system prompt for this completion")
        else:
            logger.debug("No tools available for this chat completion")
        
        # Store MCP tools locally for later execution (no longer passing to model)
        self._mcp_tools = mcp_tools

        # Log the full system prompt before sending to model
        logger.debug(f"=== SYSTEM MESSAGE FOR THIS COMPLETION ===\n{self._messages[0]['content']}\n=== END SYSTEM MESSAGE ===")

        # Build llama-cpp friendly payload (attach images as data URLs)
        model_messages = self._prepare_messages_for_llama(self._messages)

        # Create and move worker to thread (no tools parameter)
        self._chat_worker = ChatWorker(self._model, model_messages)
        self._chat_thread = QtCore.QThread()
        self._chat_worker.moveToThread(self._chat_thread)
        self._streaming_response = ""  # Buffer for collecting response chunks

        # Connect signals
        self._chat_worker.chunk_ready.connect(self._on_chunk_ready)
        self._chat_worker.finished.connect(self._on_chat_finished)
        self._chat_worker.error_occurred.connect(self._on_chat_error)
        self._chat_worker.usage_ready.connect(self._on_usage_ready)

        # Create an immediate placeholder assistant bubble for streaming
        self._append_to_history("", append_only=True, message_type="assistant")

        # Start thread
        self._chat_thread.started.connect(self._chat_worker.run)
        self._chat_thread.start()

    def _run_model_with_tool_handling(self) -> str:
        """Run model completion with automatic tool call detection and execution.
        
        This implements the multi-turn conversation loop:
        1. Run model to get response
        2. If response contains [TOOL_REQUEST], execute the tool
        3. Append tool result in [TOOL_RESULT] tags
        4. Run model again with result in conversation
        5. Repeat until model stops requesting tools or hits safety limit
        
        Returns:
            Final model response (after all tool calls executed)
        """
        MAX_TOOL_ITERATIONS = 5  # Prevent infinite loops
        MAX_TOOL_CALLS_PER_ITERATION = 10  # Safety limit on calls per response
        tool_iteration = 0
        final_response = ""
        
        while tool_iteration < MAX_TOOL_ITERATIONS:
            tool_iteration += 1
            logger.info(f"Tool handling iteration {tool_iteration}/{MAX_TOOL_ITERATIONS}")
            
            # Wait for the current chat worker to finish and get response
            if self._chat_thread:
                self._chat_thread.quit()
                self._chat_thread.wait()
            
            response = self._streaming_response.strip()
            self._streaming_response = ""
            
            logger.debug(f"[Tool Loop] Iteration {tool_iteration}: Got response ({len(response)} chars)")
            
            if not response:
                logger.warning(f"[Tool Loop] Empty response at iteration {tool_iteration}")
                break
            
            # Add response to message history
            self._messages.append({"role": "assistant", "content": response})
            final_response = response
            
            # Parse for ALL tool requests in this response
            tool_calls = []
            remaining_text = response
            
            for _ in range(MAX_TOOL_CALLS_PER_ITERATION):
                tool_request = self._parse_tool_request(remaining_text)
                if not tool_request:
                    break
                    
                tool_calls.append(tool_request)
                logger.info(f"[Tool Loop] Found tool call: {tool_request[0]}")
                
                # Remove this tool request from remaining text (to find next one)
                # This is a simple approach - could be improved
                break  # For now, handle one tool at a time
            
            if not tool_calls:
                logger.info(f"[Tool Loop] No tool requests in iteration {tool_iteration}, finishing")
                break
            
            # Execute all detected tool calls
            for tool_name, arguments in tool_calls:
                logger.info(f"[Tool Loop] Executing: {tool_name}({arguments})")
                tool_result = self._execute_tool_call(tool_name, arguments)
                
                if not tool_result:
                    error_msg = f"Tool execution failed: {tool_name}"
                    logger.error(f"[Tool Loop] {error_msg}")
                    tool_result = f"[TOOL_RESULT]\\nError: {error_msg}\\n[END_TOOL_RESULT]"
                else:
                    # Result already has tags from _format_tool_result()
                    if not tool_result.startswith("[TOOL_RESULT]"):
                        tool_result = f"[TOOL_RESULT]\\n{tool_result}\\n[END_TOOL_RESULT]"
                
                # Append tool result to conversation for model to see
                self._messages.append({"role": "user", "content": tool_result})
                logger.info(f"[Tool Loop] Added tool result to conversation: {len(tool_result)} chars")
            
            # Run model again with tool results in context
            logger.info(f"[Tool Loop] Re-running model with tool results...")
            model_messages = self._prepare_messages_for_llama(self._messages)
            self._chat_worker = ChatWorker(self._model, model_messages)
            self._chat_thread = QtCore.QThread()
            self._chat_worker.moveToThread(self._chat_thread)
            self._streaming_response = ""
            
            # Connect signals
            self._chat_worker.chunk_ready.connect(self._on_chunk_ready)
            self._chat_worker.finished.connect(self._on_chat_finished_tool_loop)
            self._chat_worker.error_occurred.connect(self._on_chat_error)
            self._chat_worker.usage_ready.connect(self._on_usage_ready)
            
            # Start and wait for completion
            self._chat_thread.started.connect(self._chat_worker.run)
            self._chat_thread.start()
            
            # Block until this iteration completes
            # (We'll be called back via _on_chat_finished_tool_loop)
            return None  # Signal that we're in a loop
        
        logger.info(f"[Tool Loop] Finished after {tool_iteration} iterations")
        return final_response

    def _on_chat_finished_tool_loop(self) -> None:
        """Callback for chat completion within tool handling loop.
        
        Different from _on_chat_finished() as it doesn't show full UI updates
        until the tool loop completes.
        """
        logger.debug("_on_chat_finished_tool_loop called")
        # Just collect the response, continue the loop
        # The main _on_chat_finished will handle display when loop is done

    def _on_chunk_ready(self, chunk: str) -> None:
        """Handle incoming chunk from the model."""
        # Collect chunks into a buffer
        self._streaming_response += chunk
        # Stream chunks directly into the current assistant bubble
        self._append_to_history(chunk, append_only=True, message_type="assistant")
    
    def _on_usage_ready(self, usage: dict) -> None:
        """Handle token usage stats from the model."""
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)
        
        if self._hwinfo_panel:
            self._hwinfo_panel.update_token_usage(usage)
        logger.info(f"Token usage - Prompt: {prompt_tokens}, Completion: {completion_tokens}, Total: {total_tokens}")

    def _on_chat_finished(self) -> None:
        """Handle chat completion with multi-turn tool handling.
        
        Implements the tool execution loop:
        1. Get initial response from model
        2. Check for [TOOL_REQUEST] blocks
        3. If found, execute tool and add result to conversation
        4. Re-run model with tool result in context
        5. Repeat until no more tool requests or safety limit hit
        6. Display final response
        """
        logger.debug("_on_chat_finished called")
        response = self._streaming_response.strip()
        self._streaming_response = ""  # Clear buffer
        
        logger.debug(f"Chat finished. Response length: {len(response)}, content: {response[:100] if response else '(empty)'}")
        
        if not response:
            logger.warning("Empty response received from model")
            print("\n" + "="*80 + "\nWARNING: Empty response from model\n" + "="*80 + "\n")
            
            # Re-enable send button
            if self._send_btn:
                self._send_btn.setEnabled(True)
                self._send_btn.setText("Send (Ctrl+Enter)")
            
            # Cleanup thread
            if self._chat_thread:
                self._chat_thread.quit()
                self._chat_thread.wait()
            
            self.processing_message = False
            return
        
        # Add initial response to message history
        self._messages.append({"role": "assistant", "content": response})
        logger.info(f"Assistant response: {response}")
        print(f"\n{'='*80}\nFULL MODEL RESPONSE ({len(response)} chars):\n{'='*80}\n{response}\n{'='*80}\n")
        # Finalize the current streaming bubble with this response
        if self._chat_panel:
            self._chat_panel.finalize_streaming_assistant(response)
        
        # Check for tool requests
        tool_request = self._parse_tool_request(response)
        
        # Cleanup thread after initial response
        if self._chat_thread:
            self._chat_thread.quit()
            self._chat_thread.wait()
        
        if tool_request:
            logger.info(f"TOOL REQUEST DETECTED: {tool_request}")
            print(f"\n{'='*80}\nTOOL REQUEST DETECTED:\n  Tool: {tool_request[0]}\n  Args: {tool_request[1]}\n{'='*80}\n")
            
            # Update the current assistant bubble to show as tool_request
            tool_name, arguments = tool_request
            if self._chat_panel:
                self._chat_panel.convert_assistant_to_tool_request(tool_name, arguments)
            
            # Execute tool and add result to conversation
            logger.info(f"[Tool Execution] Executing: {tool_name}({arguments})")
            
            tool_result = self._execute_tool_call(tool_name, arguments)
            if not tool_result:
                error_msg = "Tool execution failed"
                logger.error(f"[Tool Execution] {error_msg}: {tool_name}")
                tool_result = f"[TOOL_RESULT]\\nError: {error_msg}\\n[END_TOOL_RESULT]"
                self._append_to_history(f"Tool error: {tool_name}", message_type="error")
            else:
                # Result already has tags from _format_tool_result()
                if not tool_result.startswith("[TOOL_RESULT]"):
                    tool_result = f"[TOOL_RESULT]\\n{tool_result}\\n[END_TOOL_RESULT]"
                
                # Display tool response with tabular view
                tool_response_data = {
                    "name": tool_name,
                    "arguments": arguments,
                    "result": tool_result
                }
                self._append_to_history("", message_type="tool_response", tool_response=tool_response_data)
            
            # Append tool result to conversation
            self._messages.append({"role": "user", "content": tool_result})
            logger.info(f"[Tool Execution] Added result to conversation: {len(tool_result)} chars")
            
            # Re-run model with tool result in context
            logger.info("[Tool Execution] Re-running model with tool result...")
            self._chat_worker = ChatWorker(self._model, self._messages)
            self._chat_thread = QtCore.QThread()
            self._chat_worker.moveToThread(self._chat_thread)
            self._streaming_response = ""
            
            # Connect signals (using same _on_chat_finished for recursive calls)
            self._chat_worker.chunk_ready.connect(self._on_chunk_ready)
            self._chat_worker.finished.connect(self._on_chat_finished)
            self._chat_worker.error_occurred.connect(self._on_chat_error)
            self._chat_worker.usage_ready.connect(self._on_usage_ready)
            
            # Start thread and return (will call _on_chat_finished recursively)
            # Create a new placeholder bubble for the next streamed assistant response
            self._append_to_history("", append_only=True, message_type="assistant")
            self._chat_thread.started.connect(self._chat_worker.run)
            self._chat_thread.start()
            return
        
        # No tool request, show the response and finish
        logger.debug("No tool request found in response")
        
        # Re-enable send button
        if self._send_btn:
            self._send_btn.setEnabled(True)
            self._send_btn.setText("Send (Ctrl+Enter)")
        
        # In automation mode, process next message after a brief delay
        self.processing_message = False
        logger.debug(f"[AUTOMATION] Finished processing, automation_mode={self.automation_mode}, pending={len(self.pending_messages) if self.pending_messages else 0}")
        if self.automation_mode and self.pending_messages:
            logger.debug("[AUTOMATION] Scheduling next message in 1000ms")
            QtCore.QTimer.singleShot(1000, self._process_next_automation_message)

    def _on_chat_error(self, error: str) -> None:
        """Handle chat error.
        
        In automation mode, logs the error and exits the application.
        In interactive mode, shows the error and allows recovery.
        """
        error_msg = f"\nSystem Error: {error}\n\n"
        self._append_to_history(error_msg)
        logger.error(f"Chat error occurred: {error}")
        
        if self._send_btn:
            self._send_btn.setEnabled(True)
            self._send_btn.setText("Send (Ctrl+Enter)")
        if self._chat_thread:
            self._chat_thread.quit()
            self._chat_thread.wait()
        
        # In automation mode, exit after logging error
        if self.automation_mode:
            logger.error(f"Exiting automation mode due to error: {error}")
            QtCore.QTimer.singleShot(1000, self.close)

    def _append_to_history(self, text: str, append_only: bool = False, message_type: str = "system", tool_response: Optional[dict] = None, image_paths: Optional[list[str]] = None) -> None:
        """Append text to the history widget.
        
        Args:
            text: Text to append
            append_only: If True, append without styling (for streaming)
            message_type: Type of message - user, assistant, system, tool, tool_response, error
            tool_response: Optional dict with tool response data (name, arguments, result)
            image_paths: Optional list of attachments to show in the bubble
        """
        if self._chat_panel:
            self._chat_panel.append_to_history(text, append_only, message_type, tool_response, image_paths)

    def _load_input_file(self, file_path: str) -> list[dict]:
        """Load messages from a file. Each line is a message, special marker 'EXIT' triggers shutdown.
        
        First line can be an image file path - if it is, the next line becomes the prompt (with image attached).
        """
        messages = []
        first_line_image = None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [line.rstrip('\n') for line in f]
            
            # Check if first line is an image file path
            if lines and not lines[0].startswith('#'):
                potential_image = lines[0].strip()
                if potential_image and Path(potential_image).exists():
                    # Check if it's an image by extension
                    ext = Path(potential_image).suffix.lower()
                    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                        first_line_image = potential_image
                        logger.info(f"First line is an image: {first_line_image}")
                        lines = lines[1:]  # Skip the image path line
            
            for line_num, line in enumerate(lines, 1):
                if not line or line.startswith('#'):
                    # Skip empty lines and comments
                    continue
                
                # Check for exit marker
                if line.upper() in ['EXIT', '#EXIT', 'QUIT', '#QUIT']:
                    messages.append({'type': 'exit', 'content': ''})
                    logger.info(f"Found exit marker at line {line_num}")
                else:
                    msg = {'type': 'message', 'content': line}
                    # Attach image to first message if present
                    if first_line_image and len(messages) == 0:
                        msg['images'] = [first_line_image]
                        logger.info(f"Loaded message 1 with image: {line[:50]}... (image: {first_line_image})")
                    else:
                        logger.info(f"Loaded message {len(messages) + 1}: {line[:50]}...")
                    messages.append(msg)
                    
        except FileNotFoundError:
            logger.error(f"Input file not found: {file_path}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error loading input file: {e}")
            sys.exit(1)
        
        return messages

    def _process_next_automation_message(self) -> None:
        """Process the next message in automation mode."""
        logger.debug(f"[AUTOMATION] Processing next - mode:{self.automation_mode}, processing:{self.processing_message}, pending:{len(self.pending_messages) if self.pending_messages else 0}")
        
        if not self.automation_mode or self.processing_message or not self.pending_messages:
            if self.processing_message:
                logger.debug("[AUTOMATION] Blocked - still processing a message")
            return
        
        if not self._model:
            logger.warning("Model not loaded, cannot process automation messages")
            QtCore.QTimer.singleShot(1000, self._process_next_automation_message)
            return
        
        next_item = self.pending_messages.pop(0)
        
        if next_item['type'] == 'exit':
            logger.info("Automation: received exit marker, closing application")
            self._schedule_shutdown()
            return
        
        # Send the message
        message_text = next_item['content']
        images = next_item.get('images', [])
        
        if images:
            logger.info(f"Automation: sending message with {len(images)} image(s): {message_text[:50]}...")
        else:
            logger.info(f"Automation: sending message: {message_text[:50]}...")
        
        if self._chat_panel:
            # Set attachments first if present
            if images:
                self._chat_panel.add_images(images)
            self._chat_panel.set_input_text(message_text)
        self.processing_message = True
        
        # Simulate button click to send
        self._on_send_message()


    def _schedule_shutdown(self) -> None:
        """Schedule application shutdown after a brief delay to ensure logs are flushed."""
        # Capture screenshot before shutting down (automation exit)
        self._capture_screenshot()
        self._capture_card_svgs()
        QtCore.QTimer.singleShot(2000, self.close)

    
    def _capture_screenshot(self) -> None:
        """Capture full window screenshot and save with session timestamp."""
        try:
            # Grab the entire main window
            pixmap = self.grab()
            
            # Save to logs folder with session timestamp
            success = pixmap.save(str(self.session_screenshot_file))
            if success:
                logger.info(f"Screenshot saved: {self.session_screenshot_file}")
            else:
                logger.warning(f"Failed to save screenshot to {self.session_screenshot_file}")
        except Exception as e:
            logger.error(f"Error capturing screenshot: {e}")
    
    def _capture_card_svgs(self) -> None:
        """Export any SVG content from the Cards panel as PNG images."""
        if not self._cards_panel:
            return
        
        try:
            # Get the card widget from the panel
            if hasattr(self._cards_panel, '_card_svg'):
                card = self._cards_panel._card_svg
                
                if not card or not hasattr(card, 'grab'):
                    logger.debug("No card widget to export")
                    return
                
                # Grab the card widget
                pixmap = card.grab()
                
                # Generate filename with card index
                log_name = self.session_screenshot_file.stem  # e.g., session_2026-01-18_22-05-20
                card_file = self.session_screenshot_file.parent / f"{log_name}_cardsvg01.png"
                
                success = pixmap.save(str(card_file))
                if success:
                    logger.info(f"Card exported: {card_file}")
                else:
                    logger.warning(f"Failed to save card to {card_file}")
            else:
                logger.debug("CardsPanel has no _card_svg widget")
        
        except Exception as e:
            logger.error(f"Error capturing card SVGs: {e}")
    
    def closeEvent(self, event):
        """Handle window close, ensuring proper cleanup."""
        # Capture screenshot and card SVGs before closing
        self._capture_screenshot()
        self._capture_card_svgs()
        
        if self._hwinfo_panel:
            self._hwinfo_panel.stop_monitoring()
        
        if self._chat_thread and self._chat_thread.isRunning():
            self._chat_thread.quit()
            self._chat_thread.wait()

        # Ensure any in-flight model load thread is stopped before teardown
        if self._load_thread and self._load_thread.isRunning():
            try:
                self._load_thread.quit()
                self._load_thread.wait(2000)
            except Exception:
                pass
        self._load_thread = None
        self._load_worker = None
        
        if self._mcp_server_process and self._mcp_server_process.poll() is None:
            self._mcp_server_process.terminate()
            try:
                self._mcp_server_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._mcp_server_process.kill()

        if hasattr(self, "_model_loader"):
            self._model_loader.stop_llama_server()
        
        logger.info("Application closing")
        event.accept()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ChatLlama - Chat interface for local LLMs with MCP support"
    )
    parser.add_argument(
        '--input-file',
        '--test-file',
        type=str,
        help='Path to a text file containing test messages (one per line). '
             'Use "EXIT" or "#EXIT" on a line to trigger application shutdown after LLM responds.'
    )
    parser.add_argument(
        '--list-models',
        action='store_true',
        help='List all available models and exit.'
    )
    parser.add_argument(
        '--model',
        type=str,
        help='Model to load on startup. Can be a relative path (e.g., "mradermacher/Huihui-LFM2-2.6B-Exp-abliterated-GGUF") '
             'or a full file path to a GGUF file (e.g., "D:\\LLM Models\\mradermacher\\gemma-3-27b-it...\\model.gguf")'
    )
    parser.add_argument(
        '--mcp-http',
        action='store_true',
        help='Start built-in MCP HTTP server (svg-layout-studio) alongside the UI.'
    )
    parser.add_argument(
        '--mcp-http-port',
        type=int,
        default=6821,
        help='Port for built-in MCP HTTP server (default: 6821).'
    )
    args = parser.parse_args()
    
    # Handle --list-models
    if args.list_models:
        models = ChatWindow._discover_models_static()
        print("\n" + "=" * 70)
        print("AVAILABLE MODELS")
        print("=" * 70)
        for i, model in enumerate(models, 1):
            print(f"{i:2d}. {model}")
        print("=" * 70)
        print(f"Total: {len(models)} models found in {MODELS_DIR}")
        print("=" * 70 + "\n")
        sys.exit(0)
    
    app = QtWidgets.QApplication(sys.argv)
    window = ChatWindow(input_file=args.input_file, selected_model=args.model)
    window.show()

    # Optional: start built-in MCP HTTP server in parallel with UI
    if getattr(args, 'mcp_http', False):
        window.start_built_in_mcp_http(port=getattr(args, 'mcp_http_port', 6821))
    
    # If in automation mode, schedule first message after UI is ready
    if window.automation_mode:
        QtCore.QTimer.singleShot(2000, window._process_next_automation_message)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

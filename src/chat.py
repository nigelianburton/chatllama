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
from pathlib import Path
from typing import Optional
from datetime import datetime

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

log_format = "%(asctime)s - %(levelname)s - %(message)s"

# Configure UTF-8 console output for Unicode support (emojis)
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

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

# Load settings from config/settings.yml
settings_file = CONFIG_DIR / "settings.yml"
if settings_file.exists():
    with open(settings_file, 'r') as f:
        settings = yaml.safe_load(f)
    logger.info(f"Loaded settings from {settings_file}")
else:
    logger.error(f"Settings file not found at {settings_file}")
    settings = {}

# Extract settings with fallbacks
lm_studio_path = settings.get("llama_cpp_path", r"C:\Users\nigel\.lmstudio\extensions\backends\llama.cpp-win-x86_64-nvidia-cuda12-avx2-1.103.2")
MODELS_DIR = Path(settings.get("models_dir", r"D:\LLM Models"))
DEFAULT_MODEL = settings.get("default_model", "mradermacher\\Huihui-LFM2-2.6B-Exp-abliterated-GGUF")
LLAMA_SERVER_PORT = settings.get("llama_server_port", 8000)
GPU_OFFLOAD_LAYERS = settings.get("gpu_offload_layers", 99)
MCP_SERVER_ENABLED = settings.get("mcp_server_enabled", True)
MCP_SERVER_COMMAND = settings.get("mcp_server_command", "python test_mcp/fashion_server/server.py")
TOOL_INTEGRATION_ENABLED = settings.get("tool_integration_enabled", True)
TOOL_PREAMBLE = settings.get("tool_preamble", "You have access to specialized tools that can help you serve the user better.")
DEFAULT_CTX = int(settings.get("default_ctx", 4096))
MODEL_CTX_OVERRIDES: dict[str, int] = settings.get("model_ctx_overrides", {}) or {}

logger.debug(f"lm_studio_path: {lm_studio_path}")
logger.debug(f"MODELS_DIR: {MODELS_DIR} (exists: {MODELS_DIR.exists()})")
logger.debug(f"DEFAULT_MODEL: {DEFAULT_MODEL}")
logger.debug(f"LLAMA_SERVER_PORT: {LLAMA_SERVER_PORT}")
logger.debug(f"GPU_OFFLOAD_LAYERS: {GPU_OFFLOAD_LAYERS}")
logger.debug(f"MCP_SERVER_ENABLED: {MCP_SERVER_ENABLED}")
logger.debug(f"MCP_SERVER_COMMAND: {MCP_SERVER_COMMAND}")

# 1. Direct llama-cpp-python to the specific llama.dll
os.environ["LLAMA_CPP_LIB"] = os.path.join(lm_studio_path, "llama.dll")
logger.debug(f"LLAMA_CPP_LIB set to: {os.environ['LLAMA_CPP_LIB']}")

# 2. Tell Windows where to find the supporting CUDA and GGML dlls
# This is crucial for Python 3.8+ on Windows
os.add_dll_directory(lm_studio_path)
logger.debug(f"Added DLL directory: {lm_studio_path}")

from llama_cpp import Llama
from PyQt6 import QtCore, QtGui, QtWidgets
from chatllama_pane_settings import SettingsPanel
from chatllama_cpp import ChatLlamaCpp
from chatllama_lmstudio import ChatLlamaLmStudio
from chatllama_pane_chat import PromptInput, ChatPanel
from chatllama_pane_cards import CardsPanel
from chatllama_pane_trace import TracePanel
from chatllama_pane_hwinfo import HardwareInfoPanel


class ModelCapabilities:
    """Detect model capabilities from GGUF metadata with caching support
    
    Tool Detection:
        Checks the tokenizer.chat_template field for tool-handling logic:
        - "if tools" pattern (Qwen3, Huihui): {%- if tools -%}
        - "render_extra_keys" pattern (Nemotron): for function calling
        
    Vision Detection:
        Checks GGUF metadata field names for vision-related keywords:
        - "vision", "visual", "image", "clip", "projector", "mmproj"
        Scans both main model and mmproj files for completeness.
        Also checks filenames for "-VL-" (Vision Language) pattern.
    
    Context Length:
        Reads from GGUF metadata fields (architecture-specific)
        
    VRAM Usage:
        Measured by briefly loading model and checking GPU memory
    """
    
    @staticmethod
    def get_capabilities(model_path: Path, measure_vram: bool = False) -> dict:
        """Detect vision and tool capabilities from GGUF file
        
        Args:
            model_path: Path to model directory
            measure_vram: Whether to load model and measure VRAM usage
        
        Returns:
            dict: {
                "has_vision": bool,      # Model supports vision/image input
                "has_tools": bool,       # Model has tool/function calling
                "context_length": int,   # Max context tokens
                "vram_mb": int,          # VRAM usage in MB (if measured)
                "display_name": str      # Friendly model name
            }
        """
        capabilities = {
            "has_vision": False,
            "has_tools": False,
            "context_length": 0,
            "vram_mb": 0,
            "display_name": model_path.stem
        }
        
        if not gguf:
            return capabilities
        
        try:
            # Try to find the GGUF file in the model directory
            gguf_files = list(model_path.glob("*.gguf"))
            if not gguf_files:
                return capabilities
            
            # Prefer main model files (non-mmproj) but also check mmproj for vision
            # Sort to prefer main model files over mmproj (vision projection files)
            main_files = [f for f in gguf_files if "mmproj" not in f.name]
            mmproj_files = [f for f in gguf_files if "mmproj" in f.name]
            
            # Main model files typically have tools/chat support
            # mmproj files have vision projection data
            preferred_file = main_files[0] if main_files else mmproj_files[0]
            
            # Read metadata from preferred file
            try:
                reader = gguf.GGUFReader(str(preferred_file))
            except Exception as e:
                logger.warning(f"Failed to read GGUF file {preferred_file}: {e}")
                return capabilities
            
            if reader.fields:
                # Get display name
                if "general.name" in reader.fields:
                    try:
                        v = reader.fields["general.name"]
                        if len(v.parts) > 3:
                            capabilities["display_name"] = bytes(v.parts[-1]).decode('utf-8', errors='ignore')
                    except:
                        pass
                
                # Detect vision from field names
                vision_keywords = ["vision", "visual", "image", "clip", "projector", "mmproj"]
                for field_name in reader.fields.keys():
                    if any(kw in field_name.lower() for kw in vision_keywords):
                        capabilities["has_vision"] = True
                        break
                
                # Also check mmproj file for vision if not found in main model
                if not capabilities["has_vision"] and mmproj_files:
                    try:
                        mmproj_reader = gguf.GGUFReader(str(mmproj_files[0]))
                        for field_name in mmproj_reader.fields.keys():
                            if any(kw in field_name.lower() for kw in vision_keywords):
                                capabilities["has_vision"] = True
                                break
                    except:
                        pass
                
                # Check filename for vision indicators (VL = Vision Language)
                if not capabilities["has_vision"]:
                    for f in gguf_files:
                        if "-vl-" in str(f).lower() or "vision" in str(f).lower():
                            capabilities["has_vision"] = True
                            break
                
                # Detect tools from chat template
                # Tools are indicated by "if tools" in the template, or render_extra_keys
                if "tokenizer.chat_template" in reader.fields:
                    try:
                        template_field = reader.fields["tokenizer.chat_template"]
                        if hasattr(template_field, 'parts') and template_field.parts:
                            template = bytes(template_field.parts[-1]).decode('utf-8', errors='ignore')
                            # Check for tool-handling markers in template
                            # These are template conditionals that enable tool support
                            tool_markers = [
                                "if tools",           # Qwen/Huihui format: {%- if tools -%}
                                "render_extra_keys",  # Nemotron format for function calling
                            ]
                            if any(marker in template for marker in tool_markers):
                                capabilities["has_tools"] = True
                    except:
                        pass
                
                # Extract context length (architecture-specific field names)
                context_fields = [
                    "llama.context_length",
                    "context_length",
                    f"{capabilities.get('architecture', 'llama')}.context_length"
                ]
                
                for field in reader.fields.keys():
                    if "context_length" in field.lower():
                        try:
                            ctx_field = reader.fields[field]
                            if hasattr(ctx_field, 'parts') and ctx_field.parts:
                                # Context length is usually stored as integer
                                capabilities["context_length"] = int.from_bytes(
                                    bytes(ctx_field.parts[-1]), byteorder='little'
                                )
                                break
                        except:
                            pass
            
            # Measure VRAM if requested
            if measure_vram and preferred_file and ".Q" in preferred_file.name:
                try:
                    import GPUtil
                    # Get GPU memory before loading
                    gpus = GPUtil.getGPUs()
                    if gpus:
                        mem_before = gpus[0].memoryUsed
                        
                        # Temporarily load model
                        logger.debug(f"Measuring VRAM for {model_path.name}...")
                        test_model = Llama(
                            model_path=str(preferred_file),
                            n_ctx=512,  # Small context for testing
                            n_gpu_layers=GPU_OFFLOAD_LAYERS,
                            verbose=False
                        )
                        
                        # Get memory after loading
                        gpus = GPUtil.getGPUs()
                        mem_after = gpus[0].memoryUsed
                        capabilities["vram_mb"] = int(mem_after - mem_before)
                        
                        # Clean up
                        del test_model
                        logger.debug(f"VRAM usage: {capabilities['vram_mb']} MB")
                except Exception as e:
                    logger.debug(f"Could not measure VRAM: {e}")
        
        except Exception as e:
            logger.debug(f"Could not read metadata for {model_path}: {e}")
        
        return capabilities






class ChatWorker(QtCore.QObject):
    """Worker thread for handling chat completions without blocking the UI."""
    finished = QtCore.pyqtSignal()
    chunk_ready = QtCore.pyqtSignal(str)
    error_occurred = QtCore.pyqtSignal(str)
    usage_ready = QtCore.pyqtSignal(dict)  # Emits token usage stats

    def __init__(self, model: Llama, messages: list[dict], parent=None):
        super().__init__(parent)
        self.model = model
        self.messages = messages
        self.usage_stats = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def run(self) -> None:
        """Stream chat completion and emit chunks."""
        try:
            response_text = ""
            # Build the completion request (tools now injected via system prompt)
            completion_kwargs = {
                "messages": self.messages,
                "stream": True
            }
            logger.debug(f"Starting chat completion with {len(self.messages)} messages")
            
            chunk_count = 0
            last_log_length = 0
            for chunk in self.model.create_chat_completion(**completion_kwargs):
                chunk_count += 1
                if chunk_count <= 5 or chunk_count % 200 == 0:
                    logger.debug(f"Chunk #{chunk_count}")
                
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    response_text += content
                    self.chunk_ready.emit(content)
                    
                    # Log accumulated text every 100 characters
                    if len(response_text) >= last_log_length + 100:
                        logger.debug(f"[Text at {len(response_text)} chars] {response_text[last_log_length:last_log_length+100]}")
                        last_log_length = len(response_text)
                
                # Capture usage stats from the final chunk
                usage = chunk.get("usage")
                if usage:
                    self.usage_stats = {
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0)
                    }
            
            logger.debug(f"Streaming complete: {chunk_count} chunks, {len(response_text)} total chars")
            logger.info(f"Final response: {response_text[:200]}..." if len(response_text) > 200 else f"Final response: {response_text}")
            
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
        self._llama_server_process = None
        self._mcp_server_process = None
        self._mcp_tools = None  # Will be populated during chat
        self._last_local_model: Optional[str] = None  # Store local model when switching modes
        self._cpp_handler: Optional[ChatLlamaCpp] = None
        self._lmstudio_handler: Optional[ChatLlamaLmStudio] = None
        
        # Automation mode for testing
        self.input_file = input_file
        self.automation_mode = input_file is not None
        self.pending_messages = []
        self.processing_message = False
        self.selected_model = selected_model  # Model specified via command line
        
        # Hardware info panel (GPU + token stats)
        self._hwinfo_panel: Optional[HardwareInfoPanel] = None
        
        self._build_ui()
        self._check_and_launch_mcp_server()
        self._load_default_model()
        if self._hwinfo_panel:
            self._hwinfo_panel.start_monitoring()
        
        # Load automation messages if in automation mode
        if self.automation_mode:
            self.pending_messages = self._load_input_file(input_file)
            logger.info(f"Automation mode: loaded {len(self.pending_messages)} messages from {input_file}")


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
        self._settings_panel = SettingsPanel(default_ctx=DEFAULT_CTX)
        self._chat_panel = ChatPanel()
        self._cards_panel = CardsPanel()
        self._trace_panel = TracePanel()

        self._cpp_handler = ChatLlamaCpp(self)
        self._lmstudio_handler = ChatLlamaLmStudio(self)

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

        if self._lmstudio_handler:
            self._settings_panel.lmstudio_panel.model_load_requested.connect(self._lmstudio_handler.load_model)
            self._settings_panel.lmstudio_panel.model_selection_changed.connect(self._lmstudio_handler.on_selection_changed)
        self._settings_panel.lmstudio_panel.ctx_changed.connect(self._on_lmstudio_ctx_changed)
        
        # Connect signals from chat panel
        self._chat_panel.send_requested.connect(lambda text: self._on_send_message())
        
        # Populate models in settings panel
        if self._cpp_handler:
            self._cpp_handler.populate_models_with_capabilities()
        if self._lmstudio_handler:
            self._lmstudio_handler.populate_models_with_capabilities()

        splitter.addWidget(settings_wrap)
        splitter.addWidget(chat_wrap)
        splitter.addWidget(cards_wrap)
        splitter.addWidget(trace_wrap)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 1)
        splitter.setStretchFactor(3, 1)

        return splitter

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
        if self._settings_panel and self._settings_panel.cpp_panel:
            return self._settings_panel.cpp_panel.model_combo
        return None
    
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
        """Static method to discover models (can be called without instance)."""
        logger.info(f"Starting model discovery in: {MODELS_DIR}")
        
        if not MODELS_DIR.exists():
            logger.error(f"MODELS_DIR does not exist: {MODELS_DIR}")
            return []
        
        models = []
        try:
            # Iterate through author folders
            for author_dir in sorted(MODELS_DIR.iterdir()):
                if not author_dir.is_dir():
                    continue
                
                logger.debug(f"Scanning author folder: {author_dir.name}")
                
                # Look for model folders within each author directory
                for model_dir in sorted(author_dir.iterdir()):
                    if not model_dir.is_dir():
                        continue
                    
                    # Check if this folder has .gguf files (or .part files being downloaded)
                    gguf_files = list(model_dir.glob("*.gguf"))
                    part_files = list(model_dir.glob("*.part"))
                    
                    if gguf_files or part_files:
                        # Store the relative path from MODELS_DIR for display
                        relative_path = model_dir.relative_to(MODELS_DIR)
                        models.append(str(relative_path))
                        logger.debug(f"Found model: {relative_path} ({len(gguf_files)} .gguf, {len(part_files)} .part)")
                    else:
                        logger.debug(f"Skipped (no .gguf files): {model_dir.name}")
            
            logger.info(f"Model discovery complete. Found {len(models)} models.")
            return sorted(models)
        except Exception as e:
            logger.error(f"Error discovering models: {e}")
            return []

    def _populate_models_with_capabilities(self) -> None:
        """Populate model combo box with model names and capability badges.
        
        Uses cached capabilities from settings.yml if available,
        otherwise scans GGUF metadata and shows progress dialog.
        """
        models = self._discover_models()
        
        # Load cached capabilities from settings
        capabilities_cache = settings.get("model_capabilities", {})
        
        # Check if we need to scan any models
        models_to_scan = [m for m in models if m not in capabilities_cache]
        
        if models_to_scan:
            logger.info(f"Scanning {len(models_to_scan)} models for capabilities...")
            # Show progress dialog while scanning
            capabilities_cache = self._scan_models_with_progress(models, capabilities_cache)
            
            # Save updated cache to settings
            self._save_capabilities_cache(capabilities_cache)
        
        # Now populate combo box with cached data
        for model_name in models:
            caps = capabilities_cache.get(model_name, {
                "has_vision": False,
                "has_tools": False,
                "context_length": 0,
                "vram_mb": 0
            })
            
            # Strip maker (parent folder) from display name
            display_name = model_name.split('/', 1)[-1] if '/' in model_name else model_name
            
            # Build display string with capability icons and badges
            icons = []
            if caps.get("has_vision"):
                icons.append("👁️")
            if caps.get("has_tools"):
                icons.append("🔧")
            
            badges = []
            if caps.get("context_length", 0) > 0:
                ctx_k = caps["context_length"] // 1000
                badges.append(f" [{ctx_k}k]")
            if caps.get("vram_mb", 0) > 0:
                vram_gb = caps["vram_mb"] / 1024
                badges.append(f" [{vram_gb:.1f}GB]")
            
            icon_prefix = " ".join(icons) + " " if icons else ""
            display_text = icon_prefix + display_name + "".join(badges)
            
            # Add to combo box (store original full path in userData)
            self._model_combo.addItem(display_text, userData=model_name)
            logger.debug(f"Added model: {display_text}")
    
    def _scan_models_with_progress(self, models: list[str], existing_cache: dict) -> dict:
        """Scan models for capabilities with progress dialog.
        
        Args:
            models: List of model paths to scan
            existing_cache: Existing capabilities cache
            
        Returns:
            Updated capabilities cache
        """
        cache = existing_cache.copy()
        
        # Create progress dialog
        progress = QtWidgets.QProgressDialog(
            "Scanning model capabilities...",
            "Cancel",
            0,
            len(models),
            self
        )
        progress.setWindowTitle("Model Scan")
        progress.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()
        
        for i, model_name in enumerate(models):
            if progress.wasCanceled():
                logger.info("Model scan cancelled by user")
                break
            
            progress.setValue(i)
            progress.setLabelText(f"Scanning {model_name}...")
            QtWidgets.QApplication.processEvents()  # Keep UI responsive
            
            # Skip if already cached
            if model_name in cache:
                continue
            
            try:
                model_dir = MODELS_DIR / model_name
                
                # Get capabilities (without VRAM measurement for speed)
                caps = ModelCapabilities.get_capabilities(model_dir, measure_vram=False)
                
                # Store in cache
                cache[model_name] = {
                    "has_vision": caps["has_vision"],
                    "has_tools": caps["has_tools"],
                    "context_length": caps["context_length"],
                    "vram_mb": caps.get("vram_mb", 0)
                }
                
                logger.debug(f"Scanned {model_name}: vision={caps['has_vision']}, tools={caps['has_tools']}, ctx={caps['context_length']}")
            
            except Exception as e:
                logger.warning(f"Failed to scan {model_name}: {e}")
                # Add default entry so we don't keep retrying
                cache[model_name] = {
                    "has_vision": False,
                    "has_tools": False,
                    "context_length": 0,
                    "vram_mb": 0
                }
        
        progress.setValue(len(models))
        progress.close()
        
        return cache
    
    def _save_capabilities_cache(self, cache: dict) -> None:
        """Save capabilities cache to settings.yml.
        
        Args:
            cache: Capabilities cache dict
        """
        try:
            # Update settings in memory
            settings["model_capabilities"] = cache
            
            # Write to file
            with open(settings_file, 'w') as f:
                yaml.dump(settings, f, default_flow_style=False, sort_keys=False)
            
            logger.info(f"Saved capabilities cache for {len(cache)} models to {settings_file}")
        except Exception as e:
            logger.error(f"Failed to save capabilities cache: {e}")
    
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
        """Load the selected local model."""
        if not model_path and self._model_combo:
            model_path = self._model_combo.currentData() or self._model_combo.currentText()
        if model_path:
            self._load_model(model_path)

    def _on_load_lmstudio_clicked(self, model_id: Optional[str] = None) -> None:
        """Load the selected LM Studio model."""
        combo = self._settings_panel.lmstudio_panel.model_combo if self._settings_panel else None
        if not model_id and combo:
            model_id = combo.currentData() or combo.currentText()
        if model_id:
            self._load_lm_studio_model(model_id)

    def _on_lmstudio_selection_changed(self, index: int) -> None:
        # Update status to reflect selected LM Studio model
        combo = self._settings_panel.lmstudio_panel.model_combo if self._settings_panel else None
        status_label = self._settings_panel.lmstudio_panel.status_label if self._settings_panel else None
        if combo and status_label:
            current = combo.itemData(index) or combo.itemText(index)
            status_label.setText(f"Selected: {current}")

    def _on_lmstudio_ctx_changed(self, value: int) -> None:
        # LM Studio context change acknowledgement
        status_label = self._settings_panel.lmstudio_panel.status_label if self._settings_panel else None
        if status_label:
            status_label.setText(f"Context set to {value}")

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
        if self._status_label:
            self._status_label.setText("MCP server: Pending")

        # Trigger tool fetch; stdio_client will spawn the server if needed
        self._fetch_and_integrate_tools()

    def _fetch_mcp_tools(self) -> Optional[list]:
        """Fetch available tools from the MCP server using MCP protocol.
        
        Uses the mcp client library to connect via stdio to the MCP server
        and call the standard tools/list endpoint.
        
        Returns:
            List of tool definitions from MCP server.
        """
        if not MCP_SERVER_ENABLED:
            logger.debug("MCP server not available for tool fetching")
            return None
        
        try:
            import asyncio
            from mcp.client.session import ClientSession
            from mcp.client.stdio import stdio_client, StdioServerParameters
            
            async def get_tools():
                # Get the MCP server command from settings
                cmd_parts = MCP_SERVER_COMMAND.split()

                try:
                    # Create StdioServerParameters; stdio_client will spawn the process
                    server_params = StdioServerParameters(
                        command=cmd_parts[0],
                        args=cmd_parts[1:] if len(cmd_parts) > 1 else [],
                        cwd=PROJECT_ROOT,
                    )

                    logger.info(f"Connecting to MCP server via stdio: {MCP_SERVER_COMMAND}")
                    async with stdio_client(server_params) as (read_stream, write_stream):
                        async with ClientSession(read_stream, write_stream) as session:
                            try:
                                await session.initialize()
                                tools_response = await session.list_tools()
                                logger.info(f"MCP list_tools returned {len(tools_response.tools)} tools")
                                return tools_response.tools
                            except Exception as list_err:
                                logger.exception(f"MCP list_tools failed: {list_err}")
                                raise
                except Exception as inner_e:
                    logger.exception(f"Failed to connect to MCP server: {inner_e}")
                    return None
            
            # Run async function in new event loop with proper error handling
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                tools = loop.run_until_complete(get_tools())
                loop.close()
                
                if tools:
                    logger.info(f"Fetched {len(tools)} tools from MCP server via MCP protocol")
                    return tools
                else:
                    logger.warning("No tools returned from MCP server")
                    return None
            except Exception as loop_e:
                logger.exception(f"Async loop error while fetching tools: {loop_e}")
                return None
            
        except Exception as e:
            logger.debug(f"Failed to fetch MCP tools via MCP protocol: {e}")
            return None

    def _build_tool_prompt(self, tools: list) -> str:
        """Build a system prompt section with tools using the preamble from settings.yml.
        
        Format matches LM Studio approach with [TOOL_REQUEST] and [END_TOOL_REQUEST] markers.
        Uses the tool_preamble from settings.yml with {tools_json} placeholder replacement.
        
        Args:
            tools: List of tool definitions (MCP ToolDescription objects)
            
        Returns:
            Formatted prompt section with tools and instructions
        """
        if not tools:
            return ""
        
        # Convert to OpenAI format first
        openai_tools = self._convert_mcp_tools_to_openai_format(tools)
        if not openai_tools:
            return ""
        
        # Format tools as JSON string
        tools_json = json.dumps(openai_tools, indent=2)
        
        # Use the preamble from settings.yml and replace {tools_json} placeholder
        tool_prompt = "\n" + TOOL_PREAMBLE.replace("{tools_json}", tools_json)
        
        logger.info(f"Built tool prompt for {len(openai_tools)} tools using settings.yml preamble")
        logger.debug(f"Tool prompt:\n{tool_prompt}")
        return tool_prompt
    
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
        
        MCP tools come as ToolDescription objects. We convert them to the format
        expected by llama-cpp-python's create_chat_completion with tools parameter.
        
        Args:
            mcp_tools: List of MCP ToolDescription objects
            
        Returns:
            List of tools in OpenAI format
        """
        if not mcp_tools:
            return []
        
        openai_tools = []
        for tool in mcp_tools:
            try:
                # MCP ToolDescription has: name, description, inputSchema
                tool_def = {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or "",
                        "parameters": tool.inputSchema if hasattr(tool, 'inputSchema') else {}
                    }
                }
                openai_tools.append(tool_def)
                logger.debug(f"Converted tool '{tool.name}' to OpenAI format")
            except Exception as e:
                logger.warning(f"Failed to convert tool {tool}: {e}")
                continue
        
        logger.info(f"Converted {len(openai_tools)} MCP tools to OpenAI format")
        # Log the actual tool definitions being sent
        for tool in openai_tools:
            logger.info(f"Tool definition: {json.dumps(tool, indent=2)}")
        return openai_tools

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
        
        tools = self._fetch_mcp_tools()
        if not tools:
            logger.warning("No tools fetched from MCP server; system prompt unchanged")
            self._messages[0]["content"] = "You are a helpful assistant."
            return
        
        # No need to format tools list - just use the preamble directly
        tool_prompt = TOOL_PREAMBLE
        
        # Update system message to include tool information
        self._messages[0]["content"] = f"You are a helpful assistant.\n\n{tool_prompt}"
        logger.info(f"Integrated {len(tools)} MCP tools into system prompt")
        self._status_label.setText("MCP server: Connected")

    def _parse_tool_request(self, text: str) -> Optional[tuple[str, dict]]:
        """Detect and parse LM Studio format tool calls from model output.
        
        Looks for [TOOL_REQUEST]...[END_TOOL_REQUEST] blocks containing JSON.
        Format: [TOOL_REQUEST]{\"name\": \"tool_name\", \"arguments\": {...}}[END_TOOL_REQUEST]
        
        Args:
            text: Model output text
            
        Returns:
            Tuple of (tool_name, arguments_dict) or None if no tool call found
        """
        # Pattern: [TOOL_REQUEST] followed by JSON dict followed by [END_TOOL_REQUEST]
        pattern = r"\[TOOL_REQUEST\]\s*(\{.*?\})\s*\[END_TOOL_REQUEST\]"
        match = re.search(pattern, text, flags=re.DOTALL)
        
        if not match:
            logger.debug("No [TOOL_REQUEST] block found in model output")
            return None
        
        json_str = match.group(1).strip()
        logger.debug(f"Found TOOL_REQUEST JSON: {json_str}")
        
        try:
            tool_call = json.loads(json_str)
            tool_name = tool_call.get("name")
            arguments = tool_call.get("arguments", {})
            
            if not tool_name:
                logger.warning("Tool call JSON missing 'name' field")
                return None
            
            logger.info(f"Parsed tool call: {tool_name} with arguments {arguments}")
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
        """Execute a tool via MCP and return formatted result text."""
        if not MCP_SERVER_ENABLED:
            logger.warning("MCP server disabled; cannot execute tool")
            return None

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
                logger.info(f"Executing MCP tool '{tool_name}' via stdio")
                async with stdio_client(server_params) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        result = await session.call_tool(tool_name, arguments or {})
                        return result

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(run_call())
            loop.close()
        except Exception as e:
            logger.error(f"Tool execution failed for {tool_name}: {e}")
            return None

        if not result:
            logger.warning(f"Tool '{tool_name}' returned no result")
            return None

        try:
            return self._format_tool_result(result)
        except Exception as e:
            logger.warning(f"Could not format tool result for {tool_name}: {e}")
            try:
                return json.dumps(result.model_dump(), indent=2)
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

    def _is_llama_server_running(self) -> bool:
        """Check if llama-server is running on localhost."""
        try:
            response = requests.get(f"http://localhost:{LLAMA_SERVER_PORT}/health", timeout=1)
            return response.status_code == 200
        except Exception:
            return False

    def _launch_llama_server(self, model_path: str) -> bool:
        """Launch llama-server with the given model.
        
        Args:
            model_path: Relative path to model from MODELS_DIR
            
        Returns:
            True if successfully launched or already running
        """
        if self._is_llama_server_running():
            logger.info(f"llama-server already running on localhost:{LLAMA_SERVER_PORT}")
            return True

        full_model_path = MODELS_DIR / model_path
        gguf_files = sorted(full_model_path.glob("*.gguf"))
        quantized = [f for f in gguf_files if "Q" in f.name.upper() and "mmproj" not in f.name.lower()]
        if not quantized:
            quantized = [f for f in gguf_files if "mmproj" not in f.name.lower()]
        
        if not quantized:
            logger.error(f"No suitable .gguf file found for llama-server in {full_model_path}")
            return False

        model_file = quantized[0]
        logger.info(f"Launching llama-server with {model_file.name}...")
        
        try:
            # Launch llama-server in background
            self._llama_server_process = subprocess.Popen(
                [
                    "llama-server",
                    "-m", str(model_file),
                    "-ngl", str(GPU_OFFLOAD_LAYERS),  # GPU layers
                    "-c", "2048",                       # Context
                    "-p", str(LLAMA_SERVER_PORT)        # Port
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
            )
            
            # Wait for server to start
            for attempt in range(10):
                time.sleep(1)
                if self._is_llama_server_running():
                    logger.info("llama-server started successfully")
                    return True
            
            logger.error("llama-server failed to start within timeout")
            return False
        except Exception as e:
            logger.exception(f"Failed to launch llama-server: {e}")
            return False
    
    def _load_model_from_full_path(self, full_path: str) -> None:
        """Load a GGUF model from a full file path.
        
        Args:
            full_path: Full path to a GGUF file, e.g., "D:\\LLM Models\\mradermacher\\gemma-3-27b...\\model.gguf"
        """
        logger.info(f"Loading model from full path: {full_path}")
        model_file = Path(full_path)
        
        if not model_file.exists():
            error_msg = f"Model file not found: {full_path}"
            logger.error(error_msg)
            self._set_status(error_msg)
            return
        
        if not model_file.suffix.lower() == ".gguf":
            error_msg = f"File is not a GGUF model: {full_path}"
            logger.error(error_msg)
            self._set_status(error_msg)
            return
        
        logger.info(f"Selected model file: {model_file.name} ({model_file.stat().st_size / (1024**3):.2f} GB)")
        
        try:
            status_msg = f"Loading {model_file.name}..."
            logger.info(status_msg)
            self._set_status(status_msg)
            QtWidgets.QApplication.processEvents()

            logger.debug(f"Attempting to load model with llama-cpp-python: {str(model_file)}")
            # Determine desired context tokens for this model
            desired_ctx = self._ctx_spin.value() if self._ctx_spin else DEFAULT_CTX
            self._model = Llama(
                model_path=str(model_file),
                n_gpu_layers=-1,
                n_ctx=desired_ctx,
                verbose=False,
            )
            self._use_llama_server = False
            
            success_msg = f"Model loaded (llama-cpp-python): {model_file.name} (ctx {desired_ctx})"
            logger.info(success_msg)
            self._set_status(success_msg)
            self._set_current_model(str(model_file))  # Update current model display
        except Exception as e:
            error_msg = f"llama-cpp-python failed: {e}"
            logger.warning(error_msg)
            
            # Fallback: Try llama-server
            logger.info("Falling back to llama-server...")
            self._set_status("Model load failed. Trying llama-server...")
            
            if self._launch_llama_server(str(model_file)):
                self._use_llama_server = True
                success_msg = f"Model loaded (llama-server): {model_file.name}"
                logger.info(success_msg)
                self._set_status(success_msg)
                self._set_current_model(str(model_file))  # Update current model display
            else:
                error_msg = f"Both llama-cpp-python and llama-server failed to load model"
                logger.error(error_msg)
                self._set_status(error_msg)

    def _load_model(self, model_path: str) -> None:
        """Load a GGUF model from the models directory.
        
        Args:
            model_path: Relative path from MODELS_DIR, e.g., "mradermacher/Qwen3-VL-8B-..."
        """
        logger.info(f"Loading model: {model_path}")
        full_model_dir = MODELS_DIR / model_path
        logger.debug(f"Full model directory: {full_model_dir}")
        logger.debug(f"Directory exists: {full_model_dir.exists()}")
        
        if not full_model_dir.exists():
            error_msg = f"Model directory not found: {full_model_dir}"
            logger.error(error_msg)
            self._set_status(error_msg)
            return

        # Find the first .gguf file (prefer quantized versions like Q4_K_S)
        gguf_files = sorted(full_model_dir.glob("*.gguf"))
        logger.debug(f"Found {len(gguf_files)} .gguf files: {[f.name for f in gguf_files]}")
        
        if not gguf_files:
            error_msg = f"No .gguf files found in {full_model_dir}"
            logger.error(error_msg)
            self._set_status(error_msg)
            return

        # Prefer quantized versions over mmproj (exclude mmproj files)
        quantized = [f for f in gguf_files if "Q" in f.name.upper() and "mmproj" not in f.name.lower()]
        if not quantized:
            # If no quantized version, try to skip mmproj and use whatever is available
            quantized = [f for f in gguf_files if "mmproj" not in f.name.lower()]
        model_file = quantized[0] if quantized else gguf_files[0]
        logger.info(f"Selected model file: {model_file.name} ({model_file.stat().st_size / (1024**3):.2f} GB)")

        try:
            status_msg = f"Loading {model_file.name}..."
            logger.info(status_msg)
            self._set_status(status_msg)
            QtWidgets.QApplication.processEvents()

            logger.debug(f"Attempting to load model with llama-cpp-python: {str(model_file)}")
            # Determine desired context tokens for this model
            desired_ctx = self._ctx_spin.value() if self._ctx_spin else DEFAULT_CTX
            self._model = Llama(
                model_path=str(model_file),
                n_gpu_layers=-1,
                n_ctx=desired_ctx,
                verbose=False,
            )
            self._use_llama_server = False
            
            # Measure and cache VRAM usage
            self._measure_and_cache_vram(model_path)
            
            success_msg = f"Model loaded (llama-cpp-python): {model_path.split(chr(92))[-1]} (ctx {desired_ctx})"
            logger.info(success_msg)
            self._set_status(success_msg)
            self._set_current_model(model_path)  # Update current model display
        except Exception as e:
            error_msg = f"llama-cpp-python failed: {e}"
            logger.warning(error_msg)
            
            # Fallback: Try llama-server
            logger.info("Falling back to llama-server...")
            self._set_status("Model load failed. Trying llama-server...")
            
            if self._launch_llama_server(model_path):
                self._use_llama_server = True
                success_msg = f"Model loaded (llama-server): {model_path.split(chr(92))[-1]}"
                logger.info(success_msg)
                self._set_status(success_msg)
                self._set_current_model(model_path)  # Update current model display
            else:
                error_msg = f"Both llama-cpp-python and llama-server failed to load model"
                logger.error(error_msg)
                self._set_status(error_msg)

    def _load_default_model(self) -> None:
        """Load the default model on startup in a non-blocking way.
        
        Supports both relative model paths (e.g., "mradermacher/Huihui-LFM2-2.6B-Exp-abliterated-GGUF")
        and full file paths to GGUF files (e.g., "D:\\LLM Models\\...\\model.gguf").
        """
        # Use selected_model if provided via command line, otherwise use DEFAULT_MODEL
        model_to_load = self.selected_model if self.selected_model else DEFAULT_MODEL
        logger.info(f"Loading default model: {model_to_load}")
        
        # Check if this is a full file path (contains .gguf or looks like a full path)
        is_full_path = ".gguf" in model_to_load.lower() or ":\\" in model_to_load or model_to_load.startswith("/")
        
        if not is_full_path and self._model_combo:
            # Find the model by userData (original path) since display text now has badges
            idx = -1
            for i in range(self._model_combo.count()):
                if self._model_combo.itemData(i) == model_to_load:
                    idx = i
                    break
            
            # If not found by userData, try text match (for backward compatibility)
            if idx < 0:
                idx = self._model_combo.findText(model_to_load)
            
            if idx >= 0:
                logger.debug(f"Found model at index {idx}")
                self._model_combo.setCurrentIndex(idx)
            else:
                logger.warning(f"Model '{model_to_load}' not found in combo box")
                logger.debug(f"Available models: {[self._model_combo.itemText(i) for i in range(self._model_combo.count())]}")
        
        self._set_status("Loading default model...")
        if is_full_path:
            QtCore.QTimer.singleShot(500, lambda: self._load_model_from_full_path(model_to_load))
        else:
            QtCore.QTimer.singleShot(500, lambda: self._load_model(model_to_load))

    def _on_mode_changed(self, mode: str) -> None:
        """Handle mode change - refresh model list from appropriate source."""
        logger.info(f"Mode changed to: {mode}")
        if mode == "lm_studio":
            # Store current local model before switching to LM Studio
            if self._model_combo and self._model_combo.count() > 0:
                self._last_local_model = self._model_combo.currentData() or self._model_combo.currentText()
                logger.debug(f"Stored local model for later: {self._last_local_model}")
            
            self._load_lm_studio_models()
            self._fetch_lm_studio_current_model()
        else:
            # Switching back to Local mode
            self._populate_models_with_capabilities()
            
            # Restore the last selected local model if available
            if self._last_local_model and self._model_combo:
                # Find and select the previously selected model
                for i in range(self._model_combo.count()):
                    if self._model_combo.itemData(i) == self._last_local_model:
                        self._model_combo.setCurrentIndex(i)
                        logger.info(f"Restored local model: {self._last_local_model}")
                        break
            
            # Update current model display for local mode
            if self._model_combo and self._model_combo.count() > 0:
                # Use userData which has the full path (maker/model-name), not just display text
                current_path = self._model_combo.currentData()
                if current_path:
                    self._set_current_model(current_path)
                else:
                    # Fallback to display text if no userData
                    self._set_current_model(self._model_combo.currentText())

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
                lm_status = self._settings_panel.lmstudio_panel.status_label if self._settings_panel else None
                if lm_status:
                    lm_status.setText("No models available from LM Studio")
                return
            
            # Clear and populate combo box
            lm_combo = self._settings_panel.lmstudio_panel.model_combo if self._settings_panel else None
            lm_status = self._settings_panel.lmstudio_panel.status_label if self._settings_panel else None
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
        
        except requests.exceptions.ConnectionError:
            logger.error(f"Could not connect to LM Studio at 127.0.0.1:{lm_studio_port}")
            if self._settings_panel and self._settings_panel.lmstudio_panel.status_label:
                self._settings_panel.lmstudio_panel.status_label.setText("Error: Could not connect to LM Studio (is it running?)")
        except Exception as e:
            logger.error(f"Error fetching models from LM Studio: {e}")
            if self._settings_panel and self._settings_panel.lmstudio_panel.status_label:
                self._settings_panel.lmstudio_panel.status_label.setText(f"Error loading LM Studio models: {e}")
    
    def _load_lm_studio_model(self, model_id: str) -> None:
        """Load a model in LM Studio by selecting it.
        
        LM Studio doesn't have an explicit load endpoint. Instead, we:
        1. Make a test API call to the /api/v0/models/{model} endpoint to verify it exists
        2. Update the UI to show the selected model
        3. When the user sends a message, LM Studio will load the model automatically
        """
        try:
            lm_studio_port = settings.get("lm_studio_port", 11013)
            # Check if the model exists by fetching its info
            url = f"http://127.0.0.1:{lm_studio_port}/api/v0/models/{model_id}"
            
            logger.info(f"Verifying model exists in LM Studio: {url}")
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            
            model_info = response.json()
            state = model_info.get("state", "unknown")
            logger.info(f"Model {model_id} state: {state}")
            
            self._set_current_model(model_id)
            lm_status = self._settings_panel.lmstudio_panel.status_label if self._settings_panel else None
            if lm_status:
                if state == "loaded":
                    lm_status.setText(f"✓ {model_id} is loaded in LM Studio")
                else:
                    lm_status.setText(f"Selected {model_id} (will load when used)")
        
        except requests.exceptions.ConnectionError:
            logger.error(f"Could not connect to LM Studio at 127.0.0.1:{lm_studio_port}")
            if self._settings_panel and self._settings_panel.lmstudio_panel.status_label:
                self._settings_panel.lmstudio_panel.status_label.setText("Error: Could not connect to LM Studio (is it running?)")
        except requests.exceptions.HTTPError as e:
            logger.error(f"Model {model_id} not found or error: {e}")
            if self._settings_panel and self._settings_panel.lmstudio_panel.status_label:
                self._settings_panel.lmstudio_panel.status_label.setText(f"Error: Model {model_id} not found in LM Studio")
        except Exception as e:
            logger.error(f"Error selecting model in LM Studio: {e}")
            if self._settings_panel and self._settings_panel.lmstudio_panel.status_label:
                self._settings_panel.lmstudio_panel.status_label.setText(f"Error selecting model: {e}")
    
    def _fetch_lm_studio_current_model(self) -> None:
        """Fetch the currently loaded model from LM Studio."""
        try:
            lm_studio_port = settings.get("lm_studio_port", 11013)
            # Use /api/v0/models endpoint to check which model is loaded
            url = f"http://127.0.0.1:{lm_studio_port}/api/v0/models"
            
            logger.info(f"Fetching current model from LM Studio: {url}")
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            models = data.get("data", [])
            
            if models:
                # Find the loaded model
                loaded_models = [m for m in models if m.get("state") == "loaded"]
                if loaded_models:
                    current_model = loaded_models[0].get("id", "unknown")
                else:
                    # If no model is loaded, show the first one
                    current_model = models[0].get("id", "unknown")
                self._set_current_model(current_model)
                logger.info(f"Current LM Studio model: {current_model}")
            else:
                logger.warning("No models returned from LM Studio")
                self._set_current_model("LM Studio (no model loaded)")
        
        except Exception as e:
            logger.warning(f"Could not fetch current model from LM Studio: {e}")
            self._set_current_model("LM Studio (connection error)")
    
    def _set_current_model(self, model_name: str) -> None:
        """Update the display of the currently loaded model."""
        label = None
        if self._settings_panel and self._settings_panel.cpp_panel:
            label = self._settings_panel.cpp_panel.current_model_label
        if label:
            display_name = model_name[-50:] if len(model_name) > 50 else model_name
            label.setText(f"Model: {display_name}")
            logger.debug(f"Updated current model display: {model_name}")
    
    def _set_status(self, message: str) -> None:
        """Update the status label in the settings panel."""
        if self._status_label:
            self._status_label.setText(message)

    def _on_model_selection_changed(self, index: int) -> None:
        """Update context spin to override or default when model selection changes."""
        if self._ctx_spin is None or self._model_combo is None:
            return
        model_path = self._model_combo.itemData(index) or self._model_combo.itemText(index)
        ctx = int(MODEL_CTX_OVERRIDES.get(model_path, DEFAULT_CTX))
        self._ctx_spin.setValue(ctx)
        
        # Show maker label if model has a parent folder
        if self._maker_label and '/' in model_path:
            maker = model_path.split('/', 1)[0]
            self._maker_label.setText(f"by {maker}")
            self._maker_label.setVisible(True)
        elif self._maker_label:
            self._maker_label.setVisible(False)
        
        self._set_status(f"Model selected. Context: {ctx} tokens")

    def _save_settings(self) -> None:
        """Persist current settings to YAML file."""
        try:
            # Update runtime settings dict
            settings["default_ctx"] = DEFAULT_CTX
            settings["model_ctx_overrides"] = MODEL_CTX_OVERRIDES
            with open(settings_file, 'w', encoding='utf-8') as f:
                yaml.safe_dump(settings, f, sort_keys=False, allow_unicode=True)
            logger.info("Settings saved with updated context overrides")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def _on_ctx_changed(self, value: int) -> None:
        """When user changes context tokens, persist per-model override to settings."""
        if self._model_combo is None:
            return
        index = self._model_combo.currentIndex()
        model_path = self._model_combo.itemData(index) or self._model_combo.itemText(index)
        MODEL_CTX_OVERRIDES[model_path] = int(value)
        logger.info(f"Context override set for {model_path}: {value}")
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

        # Add user message to history and messages
        self._append_to_history(user_input, message_type="user")
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

        # Fetch MCP tools and inject as text into system prompt
        # Format matches LM Studio's approach: text-based tool list with [TOOL_REQUEST] markers
        mcp_tools = self._fetch_mcp_tools()
        if mcp_tools:
            tool_prompt = self._build_tool_prompt(mcp_tools)
            if tool_prompt:
                # Inject into system message
                if self._messages[0]["role"] == "system":
                    self._messages[0]["content"] += tool_prompt
                else:
                    # Shouldn't happen, but handle gracefully
                    logger.warning("First message is not system message, skipping tool injection")
                logger.info(f"Injected {len(mcp_tools)} tools into system prompt")
        
        # Store MCP tools locally for later execution (no longer passing to model)
        self._mcp_tools = mcp_tools

        # Create and move worker to thread (no tools parameter)
        self._chat_worker = ChatWorker(self._model, self._messages)
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
            self._chat_worker = ChatWorker(self._model, self._messages)
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

    def _append_to_history(self, text: str, append_only: bool = False, message_type: str = "system", tool_response: Optional[dict] = None) -> None:
        """Append text to the history widget.
        
        Args:
            text: Text to append
            append_only: If True, append without styling (for streaming)
            message_type: Type of message - user, assistant, system, tool, tool_response, error
            tool_response: Optional dict with tool response data (name, arguments, result)
        """
        if self._chat_panel:
            self._chat_panel.append_to_history(text, append_only, message_type, tool_response)

    def _load_input_file(self, file_path: str) -> list[dict]:
        """Load messages from a file. Each line is a message, special marker 'EXIT' triggers shutdown."""
        messages = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.rstrip('\n')
                    if not line or line.startswith('#'):
                        # Skip empty lines and comments
                        continue
                    
                    # Check for exit marker
                    if line.upper() in ['EXIT', '#EXIT', 'QUIT', '#QUIT']:
                        messages.append({'type': 'exit', 'content': ''})
                        logger.info(f"Found exit marker at line {line_num}")
                    else:
                        messages.append({'type': 'message', 'content': line})
                        logger.info(f"Loaded message {len(messages)}: {line[:50]}...")
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
        logger.info(f"Automation: sending message: {message_text[:50]}...")
        if self._chat_panel:
            self._chat_panel.set_input_text(message_text)
        self.processing_message = True
        
        # Simulate button click to send
        self._on_send_message()


    def _schedule_shutdown(self) -> None:
        """Schedule application shutdown after a brief delay to ensure logs are flushed."""
        QtCore.QTimer.singleShot(2000, self.close)

    
    def closeEvent(self, event):
        """Handle window close, ensuring proper cleanup."""
        if self._hwinfo_panel:
            self._hwinfo_panel.stop_monitoring()
        
        if self._chat_thread and self._chat_thread.isRunning():
            self._chat_thread.quit()
            self._chat_thread.wait()
        
        if self._mcp_server_process and self._mcp_server_process.poll() is None:
            self._mcp_server_process.terminate()
            try:
                self._mcp_server_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._mcp_server_process.kill()
        
        if self._llama_server_process and self._llama_server_process.poll() is None:
            self._llama_server_process.terminate()
            try:
                self._llama_server_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._llama_server_process.kill()
        
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
    
    # If in automation mode, schedule first message after UI is ready
    if window.automation_mode:
        QtCore.QTimer.singleShot(2000, window._process_next_automation_message)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

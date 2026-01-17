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



class PromptInput(QtWidgets.QTextEdit):
    """Custom QTextEdit that sends on Enter (unless Ctrl is held)."""
    send_requested = QtCore.pyqtSignal()
    
    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """Handle key press: Enter sends, Ctrl+Enter adds newline."""
        if event.key() == QtCore.Qt.Key.Key_Return or event.key() == QtCore.Qt.Key.Key_Enter:
            if event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier:
                # Ctrl+Enter: add newline
                super().keyPressEvent(event)
            else:
                # Enter alone: send message
                self.send_requested.emit()
        else:
            super().keyPressEvent(event)


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
            for chunk in self.model.create_chat_completion(messages=self.messages, stream=True):
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    response_text += content
                    self.chunk_ready.emit(content)
                
                # Capture usage stats from the final chunk
                usage = chunk.get("usage")
                if usage:
                    self.usage_stats = {
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0)
                    }
            
            # Emit usage stats if available
            if self.usage_stats["total_tokens"] > 0:
                self.usage_ready.emit(self.usage_stats)
            
            self.finished.emit()
        except Exception as e:
            self.error_occurred.emit(str(e))


class SettingsPanel(QtWidgets.QWidget):
    """Settings panel widget with model selection and configuration."""
    model_load_requested = QtCore.pyqtSignal(str)  # Emits model path
    model_selection_changed = QtCore.pyqtSignal(int)  # Emits index
    ctx_changed = QtCore.pyqtSignal(int)  # Emits context value
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsPanel")
        self.setMinimumWidth(384)
        self.setMaximumWidth(384)
        
        self.model_combo: Optional[QtWidgets.QComboBox] = None
        self.model_load_btn: Optional[QtWidgets.QPushButton] = None
        self.maker_label: Optional[QtWidgets.QLabel] = None
        self.status_label: Optional[QtWidgets.QLabel] = None
        self.ctx_spin: Optional[QtWidgets.QSpinBox] = None
        
        self._build_ui()
    
    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(QtWidgets.QLabel("Settings"))

        # Model loading UI
        model_label = QtWidgets.QLabel("Model:")
        self.model_combo = QtWidgets.QComboBox()

        self.model_load_btn = QtWidgets.QPushButton("Load Model")
        self.model_load_btn.clicked.connect(self._on_load_clicked)
        self.model_combo.currentIndexChanged.connect(self._on_selection_changed)

        layout.addWidget(model_label)
        layout.addWidget(self.model_combo)
        
        # Maker label (shown only when model selected)
        self.maker_label = QtWidgets.QLabel("")
        self.maker_label.setStyleSheet("font-size: 9px; color: #888888; font-style: italic;")
        self.maker_label.setVisible(False)
        layout.addWidget(self.maker_label)
        
        layout.addWidget(self.model_load_btn)

        # Context tokens control
        ctx_row = QtWidgets.QHBoxLayout()
        ctx_label = QtWidgets.QLabel("Context (tokens):")
        self.ctx_spin = QtWidgets.QSpinBox()
        self.ctx_spin.setRange(512, 1048576)
        self.ctx_spin.setSingleStep(512)
        self.ctx_spin.setValue(DEFAULT_CTX)
        self.ctx_spin.valueChanged.connect(self._on_ctx_changed)
        ctx_row.addWidget(ctx_label)
        ctx_row.addWidget(self.ctx_spin, 1)
        ctx_row_widget = QtWidgets.QWidget()
        ctx_row_widget.setLayout(ctx_row)
        layout.addWidget(ctx_row_widget)

        # Status label
        self.status_label = QtWidgets.QLabel("Ready")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("font-size: 10px; color: #aaaaaa;")
        layout.addWidget(self.status_label)

        layout.addStretch(1)
        self.setLayout(layout)
    
    def _on_load_clicked(self) -> None:
        """Emit signal when load button clicked."""
        if self.model_combo:
            model_path = self.model_combo.currentData() or self.model_combo.currentText()
            self.model_load_requested.emit(model_path)
    
    def _on_selection_changed(self, index: int) -> None:
        """Emit signal when model selection changes."""
        self.model_selection_changed.emit(index)
    
    def _on_ctx_changed(self, value: int) -> None:
        """Emit signal when context value changes."""
        self.ctx_changed.emit(value)


class ChatPanel(QtWidgets.QWidget):
    """Chat panel widget with history and input."""
    send_requested = QtCore.pyqtSignal(str)  # Emits message text
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ChatPanel")
        
        self.history_widget: Optional[QtWidgets.QPlainTextEdit] = None
        self.prompt_input: Optional[PromptInput] = None
        self.send_btn: Optional[QtWidgets.QPushButton] = None
        
        self._build_ui()
    
    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        chat_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        chat_splitter.setHandleWidth(2)

        self.history_widget = QtWidgets.QPlainTextEdit()
        self.history_widget.setReadOnly(True)
        self.history_widget.setPlaceholderText("Chat history will appear here...")

        self.prompt_input = PromptInput()
        self.prompt_input.setPlaceholderText("Type your message here... (Enter to send, Ctrl+Enter for newline)")
        self.prompt_input.send_requested.connect(self._on_send)

        # Send button
        self.send_btn = QtWidgets.QPushButton("Send")
        self.send_btn.clicked.connect(self._on_send)
        self.prompt_input.setMaximumHeight(120)

        # Bottom panel for prompt + send button
        prompt_panel = QtWidgets.QWidget()
        prompt_layout = QtWidgets.QVBoxLayout()
        prompt_layout.setContentsMargins(0, 0, 0, 0)
        prompt_layout.setSpacing(6)
        prompt_layout.addWidget(self.prompt_input)
        prompt_layout.addWidget(self.send_btn)
        prompt_panel.setLayout(prompt_layout)

        chat_splitter.addWidget(self.history_widget)
        chat_splitter.addWidget(prompt_panel)
        chat_splitter.setSizes([700, 300])

        layout.addWidget(QtWidgets.QLabel("Chat"))
        layout.addWidget(chat_splitter, 1)
        self.setLayout(layout)
    
    def _on_send(self) -> None:
        """Emit signal when send is requested."""
        if self.prompt_input:
            text = self.prompt_input.toPlainText().strip()
            if text:
                self.send_requested.emit(text)
    
    def append_to_history(self, text: str, append_only: bool = False) -> None:
        """Append text to history widget."""
        if not self.history_widget:
            return
        if append_only:
            self.history_widget.moveCursor(QtGui.QTextCursor.MoveOperation.End)
            self.history_widget.insertPlainText(text)
        else:
            self.history_widget.appendPlainText(text)
        self.history_widget.moveCursor(QtGui.QTextCursor.MoveOperation.End)
    
    def clear_input(self) -> None:
        """Clear the prompt input field."""
        if self.prompt_input:
            self.prompt_input.clear()
    
    def get_history_text(self) -> str:
        """Get all text from history widget."""
        if self.history_widget:
            return self.history_widget.toPlainText()
        return ""
    
    def set_input_text(self, text: str) -> None:
        """Set text in the input field."""
        if self.prompt_input:
            self.prompt_input.setPlainText(text)


class CardsPanel(QtWidgets.QWidget):
    """Cards panel widget for future features."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CardsPanel")
        self._build_ui()
    
    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(QtWidgets.QLabel("Cards"))
        layout.addStretch(1)
        self.setLayout(layout)


class ChatWindow(QtWidgets.QMainWindow):
    def __init__(self, input_file: Optional[str] = None, selected_model: Optional[str] = None) -> None:
        super().__init__()
        self.setWindowTitle("ChatLlama")
        self.resize(1400, 900)
        self._settings_panel: Optional[SettingsPanel] = None
        self._chat_panel: Optional[ChatPanel] = None
        self._cards_panel: Optional[CardsPanel] = None
        self._main_splitter = None
        self._settings_collapsed = False
        self._model = None
        self._messages: list[dict] = [
            {"role": "system", "content": "You are a helpful assistant."}
        ]
        self._chat_thread: Optional[QtCore.QThread] = None
        self._chat_worker: Optional[ChatWorker] = None
        self._use_llama_server = False
        self._llama_server_process = None
        self._mcp_server_process = None
        
        # Automation mode for testing
        self.input_file = input_file
        self.automation_mode = input_file is not None
        self.pending_messages = []
        self.processing_message = False
        self.selected_model = selected_model  # Model specified via command line
        
        # GPU monitoring
        self._gpu_samples: list[tuple[float, float]] = []  # (vram_used_mb, utilization_pct)
        self._gpu_timer: Optional[QtCore.QTimer] = None
        self._last_token_usage: dict = {}  # Track last token usage for status bar
        
        self._build_ui()
        self._check_and_launch_mcp_server()
        self._load_default_model()
        self._start_gpu_monitoring()
        
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

        toolbar = self._build_toolbar()
        self._main_splitter = self._build_main_splitter()

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

        toggle_btn = QtWidgets.QPushButton("☰")
        toggle_btn.setMaximumWidth(48)
        toggle_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        toggle_btn.clicked.connect(self._toggle_settings)
        layout.addWidget(toggle_btn)

        bar.setLayout(layout)
        return bar

    def _build_main_splitter(self) -> QtWidgets.QSplitter:
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)

        # Create panel widgets
        self._settings_panel = SettingsPanel()
        self._chat_panel = ChatPanel()
        self._cards_panel = CardsPanel()
        
        # Connect signals from settings panel
        self._settings_panel.model_load_requested.connect(self._on_load_model_clicked)
        self._settings_panel.model_selection_changed.connect(self._on_model_selection_changed)
        self._settings_panel.ctx_changed.connect(self._on_ctx_changed)
        
        # Connect signals from chat panel
        self._chat_panel.send_requested.connect(lambda text: self._on_send_message())
        
        # Populate models in settings panel
        self._populate_models_with_capabilities()

        splitter.addWidget(self._settings_panel)
        splitter.addWidget(self._chat_panel)
        splitter.addWidget(self._cards_panel)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 1)
        splitter.setSizes([384, 1000, 1000])

        return splitter

    def _toggle_settings(self) -> None:
        if not self._settings_panel or not self._main_splitter:
            return

        if self._settings_collapsed:
            self._settings_panel.setMaximumWidth(384)
            self._main_splitter.setSizes([384, 1000, 1000])
            self._settings_collapsed = False
        else:
            self._settings_panel.setMaximumWidth(0)
            self._main_splitter.setSizes([0, 1000, 1000])
            self._settings_collapsed = True
    
    # Properties for backwards compatibility with old direct widget access
    @property
    def _model_combo(self):
        return self._settings_panel.model_combo if self._settings_panel else None
    
    @property
    def _status_label(self):
        return self._settings_panel.status_label if self._settings_panel else None
    
    @property
    def _ctx_spin(self):
        return self._settings_panel.ctx_spin if self._settings_panel else None
    
    @property
    def _maker_label(self):
        return self._settings_panel.maker_label if self._settings_panel else None
    
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

    def _on_load_model_clicked(self) -> None:
        """Load the selected model from the combo box."""
        if not self._model_combo:
            return
        # Get the original model path from userData
        model_path = self._model_combo.currentData()
        if not model_path:
            # Fallback to current text if userData not set
            model_path = self._model_combo.currentText()
        if model_path:
            self._load_model(model_path)

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

    def _format_tools_for_prompt(self, tools: list) -> str:
        """Format tool definitions into a readable prompt section.
        
        Args:
            tools: List of tool definitions from MCP server
            
        Returns:
            Formatted string describing available tools
        """
        if not tools:
            return ""
        
        tools_text = "\n".join([
            f"  • {tool.name}: {tool.description}"
            for tool in tools
        ])
        return tools_text

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
        
        tools_list = self._format_tools_for_prompt(tools)
        tool_prompt = TOOL_PREAMBLE.format(tools_list=tools_list)
        
        # Update system message to include tool information
        self._messages[0]["content"] = f"You are a helpful assistant.\n\n{tool_prompt}"
        logger.info(f"Integrated {len(tools)} MCP tools into system prompt")
        self._status_label.setText("MCP server: Connected")

    def _parse_tool_request(self, text: str) -> Optional[tuple[str, dict]]:
        """Detect and parse tool invocation hints from model output."""
        pattern = r"TOOL:\s*([A-Za-z0-9_\-]+)(?:\s+with\s*\[(.*?)\])?"
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            return None

        tool_name = match.group(1).strip()
        raw_params = match.group(2)
        args: dict[str, str] = {}

        if raw_params:
            for part in raw_params.split(","):
                if not part.strip():
                    continue
                if "=" in part:
                    key, value = part.split("=", 1)
                    args[key.strip()] = value.strip().strip('"').strip("'")
                else:
                    # Positional-like value; store with numeric key for visibility
                    anon_key = f"arg{len(args)+1}"
                    args[anon_key] = part.strip()

        if not tool_name:
            return None
        return tool_name, args

    def _format_tool_result(self, result) -> str:
        """Convert MCP CallToolResult into readable text for the transcript."""
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
            return (text[:4000] + "\n... [truncated]") if len(text) > 4000 else text

        try:
            return json.dumps(result.model_dump(), indent=2)
        except Exception:
            return str(result)

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
        self._append_to_history(f"\n[Tool requested] {tool_name} {args}\n")

        # Keep automation blocked while executing tool
        self.processing_message = True
        if self._send_btn:
            self._send_btn.setEnabled(False)
            self._send_btn.setText("Running tool...")

        tool_output = self._execute_tool_call(tool_name, args)
        if not tool_output:
            self._append_to_history(f"[Tool failed] {tool_name}\n")
            logger.error(f"Tool execution failed or returned empty result: {tool_name}")
            self.processing_message = False
            if self._send_btn:
                self._send_btn.setEnabled(True)
                self._send_btn.setText("Send (Ctrl+Enter)")
            if self.automation_mode and self.pending_messages:
                QtCore.QTimer.singleShot(1000, self._process_next_automation_message)
            return

        tool_message = f"Tool {tool_name} result:\n{tool_output}"
        # Append readable output to history
        self._append_to_history(tool_message + "\n")
        # Provide tool result to model as assistant content (avoids extra system messages)
        self._messages.append({"role": "assistant", "content": tool_message})

        # Prune message history to keep context under control (keep last 8 entries + system)
        try:
            base_system = self._messages[0]
            tail = self._messages[-8:]
            self._messages = [base_system] + tail
        except Exception:
            pass

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
            else:
                error_msg = f"Both llama-cpp-python and llama-server failed to load model"
                logger.error(error_msg)
                self._set_status(error_msg)

    def _load_default_model(self) -> None:
        """Load the default model on startup in a non-blocking way."""
        # Use selected_model if provided via command line, otherwise use DEFAULT_MODEL
        model_to_load = self.selected_model if self.selected_model else DEFAULT_MODEL
        logger.info(f"Loading default model: {model_to_load}")
        
        if self._model_combo:
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
        QtCore.QTimer.singleShot(500, lambda: self._load_model(model_to_load))

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

        # Log the message being sent (especially important in automation mode)
        logger.info(f"User message: {user_input}")

        # Add user message to history and messages
        self._append_to_history(f"You: {user_input}\n")
        self._messages.append({"role": "user", "content": user_input})
        self._prompt_input.clear()

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

        # Create and move worker to thread
        self._chat_worker = ChatWorker(self._model, self._messages)
        self._chat_thread = QtCore.QThread()
        self._chat_worker.moveToThread(self._chat_thread)

        # Connect signals
        self._chat_worker.chunk_ready.connect(self._on_chunk_ready)
        self._chat_worker.finished.connect(self._on_chat_finished)
        self._chat_worker.error_occurred.connect(self._on_chat_error)
        self._chat_worker.usage_ready.connect(self._on_usage_ready)

        # Start thread
        self._chat_thread.started.connect(self._chat_worker.run)
        self._chat_thread.start()

    def _on_chunk_ready(self, chunk: str) -> None:
        """Handle incoming chunk from the model."""
        self._append_to_history(chunk, append_only=True)
    
    def _on_usage_ready(self, usage: dict) -> None:
        """Handle token usage stats from the model."""
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)
        
        # Store for status bar display
        self._last_token_usage = {
            "prompt": prompt_tokens,
            "completion": completion_tokens,
            "total": total_tokens
        }
        
        logger.info(f"Token usage - Prompt: {prompt_tokens}, Completion: {completion_tokens}, Total: {total_tokens}")

    def _on_chat_finished(self) -> None:
        """Handle chat completion."""
        self._append_to_history("\n\n")

        # Extract full response and add to messages
        current_text = self._history_widget.toPlainText() if self._history_widget else ""
        # Find the last assistant response by looking backward from end
        lines = current_text.split("\n")
        response_lines = []
        for line in reversed(lines):
            if line.startswith("You:"):
                break
            response_lines.insert(0, line)
        response = "\n".join(response_lines).strip()

        if response:
            self._messages.append({"role": "assistant", "content": response})
            logger.info(f"Assistant response: {response}")

        tool_request = self._parse_tool_request(response) if response else None

        # Re-enable send button only when not chaining a tool call
        if not tool_request and self._send_btn:
            self._send_btn.setEnabled(True)
            self._send_btn.setText("Send (Ctrl+Enter)")

        # Cleanup thread
        if self._chat_thread:
            self._chat_thread.quit()
            self._chat_thread.wait()

        # If the model asked for a tool, execute it before moving on
        if tool_request:
            self._handle_tool_request(tool_request)
            return

        # In automation mode, process next message after a brief delay
        self.processing_message = False
        if self.automation_mode and self.pending_messages:
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

    def _append_to_history(self, text: str, append_only: bool = False) -> None:
        """Append text to the history widget."""
        if self._chat_panel:
            self._chat_panel.append_to_history(text, append_only)

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
        if not self.automation_mode or self.processing_message or not self.pending_messages:
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

    def _start_gpu_monitoring(self) -> None:
        """Start polling GPU stats every second."""
        try:
            import GPUtil
            self._gpu_timer = QtCore.QTimer()
            self._gpu_timer.timeout.connect(self._update_gpu_stats)
            self._gpu_timer.start(1000)  # Poll every second
            logger.debug("GPU monitoring started")
        except ImportError:
            logger.debug("GPUtil not available; GPU monitoring disabled")
    
    def _update_gpu_stats(self) -> None:
        """Poll GPU and update status bar with rolling average."""
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if not gpus:
                return
            
            gpu = gpus[0]
            vram_used = gpu.memoryUsed  # MB
            utilization = gpu.load * 100  # Percent
            
            # Only add non-zero readings
            if vram_used > 0 or utilization > 0:
                self._gpu_samples.append((vram_used, utilization))
                # Keep only last 10 samples
                if len(self._gpu_samples) > 10:
                    self._gpu_samples.pop(0)
            
            # Calculate averages from non-zero samples
            if self._gpu_samples:
                avg_vram = sum(s[0] for s in self._gpu_samples) / len(self._gpu_samples)
                avg_util = sum(s[1] for s in self._gpu_samples) / len(self._gpu_samples)
                status_msg = f"GPU: {avg_vram:.0f} MB VRAM | {avg_util:.1f}% Util"
                
                # Append token usage if available
                if self._last_token_usage:
                    prompt = self._last_token_usage.get("prompt", 0)
                    completion = self._last_token_usage.get("completion", 0)
                    total = self._last_token_usage.get("total", 0)
                    status_msg += f" | Tokens: {total} ({prompt}+{completion})"
                
                self.statusBar().showMessage(status_msg)
        except Exception as e:
            logger.debug(f"GPU stats update failed: {e}")
    
    def closeEvent(self, event):
        """Handle window close, ensuring proper cleanup."""
        if self._gpu_timer:
            self._gpu_timer.stop()
        
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
        help='Model to load on startup (e.g., "mradermacher/Huihui-LFM2-2.6B-Exp-abliterated-GGUF")'
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

"""Model discovery and capability detection for ChatLlama.

Simplified design (llama-server only):
- Always discovers models fresh from disk (no persistent lists)
- Computes capabilities (vision/tools/context) on demand per discovered model
- Settings.yml stores only the most recently used model name (key: "last_model")
- All model loading uses llama-server backend exclusively
"""

import sys
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Tuple

import requests
import yaml
import psutil
from PyQt6 import QtWidgets, QtCore

try:
    import gguf
except ImportError:
    gguf = None

logger = logging.getLogger(__name__)


@dataclass
class LoadResult:
    success: bool
    model: object | None
    used_llama_server: bool
    message: str
    error: Optional[str] = None
    model_file: Optional[Path] = None
    model_rel: Optional[str] = None


def load_settings(settings_file: Path) -> dict:
    """Load settings.yml and extract configuration with defaults.
    
    If settings file doesn't exist, creates it with default values.
    
    Args:
        settings_file: Path to settings.yml
        
    Returns:
        Dictionary with extracted settings including:
        - llama_server_path, models_dir, default_model
        - llama_server_port, gpu_offload_layers
        - mcp_server_enabled, mcp_server_command
        - tool_integration_enabled, tool_preamble, default_ctx
        - last_model (from settings or None)
        - model_capabilities (cached capabilities)
    """
    # Create default settings if file doesn't exist
    if not settings_file.exists():
        logger.info(f"Settings file not found at {settings_file}; creating with defaults")
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        default_settings = {
            "llama_cpp_path": r"C:\Llama",
            "models_dir": r"D:\LLM Models",
            "default_model": r"mradermacher\Huihui-LFM2-2.6B-Exp-abliterated-GGUF",
            "llama_server_port": 8017,
            "default_ctx": 16384,
            "gpu_offload_layers": 99,
            "use_llama_server_for_all": True,
            "mcp_server_enabled": True,
            "mcp_server_command": "python test_mcp/fashion_stdio.py",
            "tool_integration_enabled": True,
            "tool_preamble": "## Available Tools\n\nYou have access to the following tools:\n\n{tools_json}\n\n### How to Invoke Tools\n\nWhen you need to use a tool, include a tool request block in your response exactly like this:\n\n[TOOL_REQUEST]\n{\"name\": \"tool_name\", \"arguments\": {\"param1\": \"value1\", \"param2\": \"value2\"}}\n[END_TOOL_REQUEST]\n\nExample 1 - Create an artboard:\n[TOOL_REQUEST]\n{\"name\": \"create_artboard\", \"arguments\": {\"orientation\": \"landscape\"}}\n[END_TOOL_REQUEST]\n\nExample 2 - Render SVG to display:\n[TOOL_REQUEST]\n{\"name\": \"render_svg\", \"arguments\": {\"artboard_guid\": \"<guid>\", \"svg\": \"<svg_markup>\"}}\n[END_TOOL_REQUEST]\n\n- Always provide the complete tool name and all required parameters\n- Tools display results in the Cards panel on the right side",
            "model_capabilities": {},
            "last_model": None
        }
        with open(settings_file, 'w') as f:
            yaml.dump(default_settings, f, default_flow_style=False, sort_keys=False)
        logger.info(f"Created default settings at {settings_file}")
    
    with open(settings_file, 'r') as f:
        settings = yaml.safe_load(f) or {}
    logger.info(f"Loaded settings from {settings_file}")
    
    extracted = {
        "llama_server_path": Path(settings.get("llama_cpp_path", r"C:\Llama")),
        "models_dir": Path(settings.get("models_dir", r"D:\LLM Models")),
        "default_model": settings.get(
            "default_model",
            "mradermacher\\Huihui-LFM2-2.6B-Exp-abliterated-GGUF"
        ),
        "llama_server_port": settings.get("llama_server_port", 8017),
        "gpu_offload_layers": settings.get("gpu_offload_layers", 99),
        "mcp_server_enabled": settings.get("mcp_server_enabled", True),
        "mcp_server_command": settings.get(
            "mcp_server_command",
            "python test_mcp/fashion_server/server.py"
        ),
        "tool_integration_enabled": settings.get("tool_integration_enabled", True),
        "tool_preamble": settings.get(
            "tool_preamble",
            "You have access to specialized tools that can help you serve the user better."
        ),
        "default_ctx": int(settings.get("default_ctx", 4096)),
        "fallback_to_llama_server": settings.get("use_llama_server_for_all", True),
        "last_model": settings.get("last_model"),  # Can be None
        "_raw_settings": settings,  # Store raw for future updates
        "model_capabilities": settings.get("model_capabilities", {}) or {},
    }
    
    # Log extracted values
    logger.debug(f"llama_server_path: {extracted['llama_server_path']}")
    logger.debug(f"models_dir: {extracted['models_dir']} (exists: {extracted['models_dir'].exists()})")
    logger.debug(f"default_model: {extracted['default_model']}")
    logger.debug(f"llama_server_port: {extracted['llama_server_port']}")
    logger.debug(f"gpu_offload_layers: {extracted['gpu_offload_layers']}")
    logger.debug(f"mcp_server_enabled: {extracted['mcp_server_enabled']}")
    logger.debug(f"mcp_server_command: {extracted['mcp_server_command']}")
    logger.debug(f"last_model: {extracted['last_model']}")
    logger.debug(f"model_capabilities cache entries: {len(extracted['model_capabilities'])}")
    
    return extracted


def kill_all_llama_servers() -> int:
    """Kill all running llama-server processes.
    
    Returns:
        Number of processes killed
    """
    killed = 0
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] and 'llama-server' in proc.info['name'].lower():
                logger.info(f"Killing llama-server process: PID {proc.info['pid']}")
                proc.kill()
                killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    if killed > 0:
        logger.info(f"Killed {killed} llama-server process(es)")
    return killed


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
    def get_capabilities(model_path: Path) -> dict:
        """Detect vision and tool capabilities from GGUF file
        
        Args:
            model_path: Path to model directory
        
        Returns:
            dict: {
                "has_vision": bool,      # Model supports vision/image input
                "has_tools": bool,       # Model has tool/function calling
                "context_length": int,   # Max context tokens
                "vram_mb": int,          # Always 0 (VRAM measurement removed)
                "file_size_mb": int,     # File size in MB
                "display_name": str      # Friendly model name
            }
        """
        capabilities = {
            "has_vision": False,
            "has_tools": False,
            "context_length": 0,
            "vram_mb": 0,
            "file_size_mb": 0,
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
            
            # Calculate file size from main model file
            if main_files:
                file_size_bytes = main_files[0].stat().st_size
                capabilities["file_size_mb"] = int(file_size_bytes / (1024 * 1024))
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
                    except Exception as e:
                        logger.debug(f"Error reading model name: {e}")
                
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
                    except Exception as e:
                        logger.debug(f"Error reading mmproj file: {e}")
                
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
                    except Exception as e:
                        logger.debug(f"Error parsing chat template: {e}")
                
                # Extract context length (architecture-specific field names)
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
                        except Exception as e:
                            logger.debug(f"Error reading context length from field {field}: {e}")
            
            # VRAM measurement removed (requires Llama class which doesn't exist in server-only mode)
        
        except Exception as e:
            logger.debug(f"Could not read metadata for {model_path}: {e}")
        
        return capabilities


class ModelValidator:
    """Manages model discovery and capability detection (stateless)."""
    
    def __init__(
        self,
        models_dir: Path,
        settings_file: Path,
        settings: dict,
        model_capabilities_class,
        parent_widget: Optional[QtWidgets.QWidget] = None
    ):
        """Initialize model validator.
        
        Args:
            models_dir: Path to models directory
            settings_file: Path to settings.yml
            settings: Settings dictionary (will be updated)
            model_capabilities_class: ModelCapabilities class for scanning
            parent_widget: Parent widget for progress dialogs
        """
        self.models_dir = models_dir
        self.settings_file = settings_file
        self.settings = settings
        self.ModelCapabilities = model_capabilities_class
        self.parent_widget = parent_widget
    
    def discover_models(self) -> list[str]:
        """Discover models from filesystem (fresh each call).

        Returns:
            List of model paths relative to models_dir
        """
        logger.info(f"Starting model discovery in: {self.models_dir}")
        
        if not self.models_dir.exists():
            logger.error(f"MODELS_DIR does not exist: {self.models_dir}")
            return []
        
        models = []
        # Iterate through author folders
        for author_dir in sorted(self.models_dir.iterdir()):
            if not author_dir.is_dir():
                continue
            
            logger.debug(f"Scanning author folder: {author_dir.name}")
            
            # Look for model folders within each author directory
            for model_dir in sorted(author_dir.iterdir()):
                if not model_dir.is_dir():
                    continue
                
                # Check if this folder has completed .gguf files
                # Note: .part files indicate incomplete downloads - only include if .gguf exists
                gguf_files = list(model_dir.glob("*.gguf"))
                part_files = list(model_dir.glob("*.part"))
                
                if gguf_files:
                    # Store the relative path from models_dir for display
                    relative_path = model_dir.relative_to(self.models_dir)
                    models.append(str(relative_path))
                    logger.debug(f"Found model: {relative_path} ({len(gguf_files)} .gguf, {len(part_files)} .part)")
                else:
                    if part_files:
                        logger.debug(f"Skipped (incomplete download): {model_dir.name} ({len(part_files)} .part files)")
                    else:
                        logger.debug(f"Skipped (no .gguf files): {model_dir.name}")
        
        logger.info(f"Model discovery complete. Found {len(models)} models.")
        return sorted(models)
    def scan_models_with_progress(
        self,
        models: list[str]
    ) -> dict:
        """Scan models for capabilities with progress dialog (fresh scan).

        Args:
            models: List of model paths to scan

        Returns:
            Capabilities map for the provided models
        """
        cache: dict = {}
        
        # Create progress dialog
        progress = QtWidgets.QProgressDialog(
            "Scanning model capabilities...",
            "Cancel",
            0,
            len(models),
            self.parent_widget
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
            
            model_dir = self.models_dir / model_name
            
            # Get capabilities
            caps = self.ModelCapabilities.get_capabilities(model_dir)
            
            # Store in cache
            cache[model_name] = {
                "has_vision": caps["has_vision"],
                "has_tools": caps["has_tools"],
                "context_length": caps["context_length"],
                "vram_mb": caps.get("vram_mb", 0),
                "file_size_mb": caps.get("file_size_mb", 0)
            }
            
            logger.debug(f"Scanned {model_name}: vision={caps['has_vision']}, tools={caps['has_tools']}, ctx={caps['context_length']}")
        
        progress.setValue(len(models))
        progress.close()
        
        return cache

    def populate_models_with_capabilities(
        self,
        model_combo: QtWidgets.QComboBox
    ) -> None:
        """Populate model combo box with model names and capability badges (fresh scan).
        Shows a modal progress dialog during discovery and scanning."""
        logger.info("ModelValidator: starting discovery and capability scan")
        # Show discovery modal (indeterminate)
        discovery = QtWidgets.QProgressDialog(
            "Discovering models...",
            "Cancel",
            0,
            0,
            self.parent_widget,
        )
        discovery.setWindowTitle("Model Discovery")
        discovery.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        discovery.setMinimumDuration(0)
        discovery.setRange(0, 0)  # Indeterminate/busy
        discovery.show()
        QtWidgets.QApplication.processEvents()

        models = self.discover_models()
        discovery.close()

        # Prune cache to discovered models and scan only missing
        capabilities_cache = self._load_capabilities_cache()
        original_cache_size = len(capabilities_cache)
        capabilities_cache = {m: capabilities_cache[m] for m in capabilities_cache if m in models}
        missing = [m for m in models if m not in capabilities_cache]

        if missing:
            logger.info(f"ModelValidator: scanning {len(missing)} new/uncached models")
            new_caps = self.scan_models_with_progress(missing)
            capabilities_cache.update(new_caps)
            self._save_capabilities_cache(capabilities_cache)
        else:
            logger.info("ModelValidator: no new models to scan; using cached capabilities")

        model_combo.clear()
        for model_name in models:
            caps = capabilities_cache.get(model_name, {
                "has_vision": False,
                "has_tools": False,
                "context_length": 0,
                "vram_mb": 0,
                "file_size_mb": 0
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
            if caps.get("file_size_mb", 0) > 0:
                size_gb = caps["file_size_mb"] / 1024
                badges.append(f" {size_gb:.1f}GB")
            if caps.get("context_length", 0) > 0:
                ctx_k = caps["context_length"] // 1000
                badges.append(f" [{ctx_k}k]")
            if caps.get("vram_mb", 0) > 0:
                vram_gb = caps["vram_mb"] / 1024
                badges.append(f" [{vram_gb:.1f}GB VRAM]")
            
            icon_prefix = " ".join(icons) + " " if icons else ""
            display_text = icon_prefix + display_name + "".join(badges)
            
            # Add to combo box (store original full path in userData)
            model_combo.addItem(display_text, userData=model_name)
            logger.debug(f"Added model: {display_text}")
        if not models:
            logger.warning("ModelValidator: no models discovered; model list is empty")
        logger.info("ModelValidator: model population finished")
        # No return (no overrides maintained)

    # ----- Last model management -----
    def get_last_model_name(self) -> Optional[str]:
        """Return the most recently used model name from settings (or None)."""
        return self.settings.get("last_model")

    def set_last_model_name(self, model_name: str) -> None:
        """Persist the most recently used model name to settings.yml only."""
        self.settings["last_model"] = model_name
        with open(self.settings_file, 'w') as f:
            yaml.dump(self.settings, f, default_flow_style=False, sort_keys=False)
        logger.info(f"Updated last_model in settings: {model_name}")

    # ----- Capability cache helpers -----
    def _load_capabilities_cache(self) -> Dict:
        return self.settings.get("model_capabilities", {}) or {}

    def _save_capabilities_cache(self, cache: Dict) -> None:
        self.settings["model_capabilities"] = cache
        with open(self.settings_file, 'w') as f:
            yaml.dump(self.settings, f, default_flow_style=False, sort_keys=False)
        logger.info(f"Saved model_capabilities cache with {len(cache)} entries")

    # ----- Async warm-up removed (llama-server only) -----
    # No longer needed since we always use llama-server


class ModelLoadWorker(QtCore.QObject):
    """Background loader that delegates to LlamaModelLoader to avoid UI blocking."""

    finished = QtCore.pyqtSignal(object)

    def __init__(self, loader: "LlamaModelLoader", model_path: str, desired_ctx: int) -> None:
        super().__init__()
        self.loader = loader
        self.model_path = model_path
        self.desired_ctx = desired_ctx

    @QtCore.pyqtSlot()
    def run(self) -> None:
        try:
            path_obj = Path(self.model_path)
            if path_obj.is_absolute():
                result = self.loader.load_model_file(path_obj, self.desired_ctx)
            else:
                result = self.loader.load_model_from_directory(self.model_path, self.desired_ctx)
        except Exception as exc:  # pragma: no cover - defensive guard
            msg = f"Model load failed: {exc}"
            result = LoadResult(False, None, True, msg, msg, path_obj if 'path_obj' in locals() else None)
        self.finished.emit(result)


class LlamaModelLoader:
    """Centralized llama-server loading and management (server-only mode)."""

    def __init__(
        self,
        models_dir: Path,
        gpu_offload_layers: int,
        port: int,
        llama_server_path: Path,
    ) -> None:
        self.models_dir = models_dir
        self.gpu_offload_layers = gpu_offload_layers
        self.port = port
        self.llama_server_path = llama_server_path
        self._llama_server_process: Optional[subprocess.Popen] = None
        
        # Kill any stray llama-server instances on startup
        self._kill_existing_llama_servers()
    
    def _kill_existing_llama_servers(self) -> None:
        """Kill any running llama-server.exe processes to ensure clean state."""
        if sys.platform != 'win32':
            return
        
        try:
            import psutil
            killed = 0
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] and 'llama-server' in proc.info['name'].lower():
                        logger.info(f"Killing existing llama-server process (PID {proc.info['pid']})")
                        proc.kill()
                        killed += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            if killed > 0:
                logger.info(f"Killed {killed} existing llama-server instance(s)")
        except ImportError:
            logger.warning("psutil not available; cannot kill existing llama-server processes")
        except Exception as e:
            logger.warning(f"Failed to kill existing llama-servers: {e}")

    @property
    def llama_server_process(self):
        return self._llama_server_process

    def resolve_model_file(self, model_path: str) -> Tuple[Optional[Path], str]:
        full_model_dir = self.models_dir / model_path
        if not full_model_dir.exists():
            return None, f"Model directory not found: {full_model_dir}"

        gguf_files = sorted(full_model_dir.glob("*.gguf"))
        if not gguf_files:
            return None, f"No .gguf files found in {full_model_dir}"

        quantized = [f for f in gguf_files if "Q" in f.name.upper() and "mmproj" not in f.name.lower()]
        if not quantized:
            quantized = [f for f in gguf_files if "mmproj" not in f.name.lower()]

        if not quantized:
            return None, f"No usable .gguf files found in {full_model_dir}"

        return quantized[0], ""

    def _is_llama_server_running(self) -> bool:
        """Test if llama-server is running on self.port.

        Criteria:
        - GET /health returns 200, or
        - GET /slots returns 200 (default enabled on llama.cpp server)
        
        Returns False if server is not reachable.
        """
        base = f"http://localhost:{self.port}"
        try:
            # Try /health endpoint
            r = requests.get(f"{base}/health", timeout=1)
            if r.status_code == 200:
                return True
            # Try /slots endpoint
            r = requests.get(f"{base}/slots", timeout=1)
            return r.status_code == 200
        except (requests.ConnectionError, requests.Timeout):
            return False

    def _port_status(self, port: int) -> str:
        """Return 'llama' if llama-server is detected, 'occupied' if something else responds, 'free' if connection fails."""
        base = f"http://localhost:{port}"
        try:
            r = requests.get(f"{base}/health", timeout=0.5)
            # Only 200 on /health is considered llama-server
            if r.status_code == 200:
                return 'llama'
            else:
                return 'occupied'
        except (requests.ConnectionError, requests.Timeout):
            return 'free'

    def _find_free_port(self, start_port: int, max_tries: int = 20) -> int | None:
        """Find an available port not occupied by other services (or already a llama-server)."""
        for p in range(start_port, start_port + max_tries):
            status = self._port_status(p)
            if status == 'free':
                return p
            if status == 'llama':
                return p
        return None

    def _launch_llama_server(self, model_file: Path, desired_ctx: int) -> bool:
        """Launch llama-server with model via -m flag.
        
        Kills all existing llama-servers first to ensure clean slate.
        This approach is compatible with all llama-server builds.
        """
        # Kill all existing llama-server processes to ensure clean slate
        kill_all_llama_servers()
        
        # Wait briefly for port to be released
        QtCore.QThread.msleep(500)
        
        # If the desired port is STILL occupied by a non-llama service, abort
        status = self._port_status(self.port)
        if status == 'occupied':
            logger.error(
                "Port %d is occupied by a non-llama-server service; stop it or change llama_server_port",
                self.port,
            )
            return False

        # Look for llama-server executable
        llama_server_exe = self.llama_server_path / "llama-server.exe"
        
        if not llama_server_exe.exists():
            raise FileNotFoundError(f"llama-server.exe not found at {llama_server_exe}")

        # Start llama-server WITH model (traditional mode - most compatible)
        logger.info(f"Launching llama-server from {llama_server_exe} on port {self.port}")
        logger.info(f"Loading model: {model_file.name}")
        self._llama_server_process = subprocess.Popen(
            [
                str(llama_server_exe),
                "-m",
                str(model_file),
                "-ngl",
                str(self.gpu_offload_layers),
                "-c",
                str(desired_ctx),
                "--port",
                str(self.port),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
        )

        # Wait for server to be ready
        for attempt in range(60):
            QtCore.QThread.msleep(1000)
            if self._is_llama_server_running():
                logger.info(f"llama-server started successfully with model {model_file.name}")
                return True
            if attempt % 10 == 0 and attempt > 0:
                logger.debug(f"Still waiting for llama-server... ({attempt}s elapsed)")
        
        logger.error("llama-server failed to start within timeout (60s)")
        return False

    def stop_llama_server(self) -> None:
        if self._llama_server_process and self._llama_server_process.poll() is None:
            self._llama_server_process.terminate()
            self._llama_server_process.wait(timeout=2)
        self._llama_server_process = None

    def unload_llama_server_model(self) -> bool:
        """Unload the current model from llama-server.

        Attempts an HTTP unload; if unsupported, stops the server process.
        Returns True if VRAM should be freed.
        """
        from chatllama_llama_server import LlamaServerClient
        client = LlamaServerClient(host="localhost", port=self.port)
        if client.is_alive():
            if client.unload_model():
                return True
            logger.info("llama-server unload endpoint unavailable; stopping server process")
        else:
            logger.info("llama-server not responding; stopping process if present")

        # Stop the server process
        self.stop_llama_server()
        return True

    def load_model_file(self, model_file: Path, desired_ctx: int) -> LoadResult:
        """Load a model file using llama-server exclusively.
        
        Args:
            model_file: Path to .gguf model file
            desired_ctx: Context window size
            
        Returns:
            LoadResult with success status and adapter or error
        """
        if not model_file.exists():
            msg = f"Model file not found: {model_file}"
            logger.error(msg)
            return LoadResult(False, None, True, msg, msg, model_file)

        if model_file.suffix.lower() != ".gguf":
            msg = f"File is not a GGUF model: {model_file}"
            logger.error(msg)
            return LoadResult(False, None, True, msg, msg, model_file)

        logger.info(f"Loading model via llama-server: {model_file.name}")
        
        if self._launch_llama_server(model_file, desired_ctx):
            # Return an adapter that wraps the llama-server client
            from chatllama_llama_server import LlamaServerClient, LlamaServerAdapter
            client = LlamaServerClient(host="localhost", port=self.port)
            adapter = LlamaServerAdapter(client)
            success_msg = f"Model loaded (llama-server): {model_file.name}"
            logger.info(success_msg)
            return LoadResult(True, adapter, True, success_msg, None, model_file)

        error_msg = "llama-server failed to load model"
        logger.error(error_msg)
        return LoadResult(False, None, True, error_msg, error_msg, model_file)

    def load_model_from_directory(self, model_path: str, desired_ctx: int) -> LoadResult:
        """Load a model from its directory path (resolves to .gguf file).
        
        Args:
            model_path: Relative path from models_dir (e.g., "author/model-name")
            desired_ctx: Context window size
            
        Returns:
            LoadResult with model_rel set to the directory path
        """
        model_file, error = self.resolve_model_file(model_path)
        if not model_file:
            return LoadResult(False, None, True, error, error, None, model_path)

        result = self.load_model_file(model_file, desired_ctx)
        result.model_rel = model_path
        return result
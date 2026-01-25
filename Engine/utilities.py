from __future__ import annotations

import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import threading
import subprocess
import sys
from pathlib import Path
from typing import Optional, Callable

from PyQt6 import QtGui, QtWidgets, QtCore

from Engine.logger import get_logger

# Try to import transformers at module level for Moondream2 support
try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from transformers import __version__ as _TRANSFORMERS_VERSION
    _TRANSFORMERS_AVAILABLE = True
except ImportError:
    _TRANSFORMERS_AVAILABLE = False
    AutoModelForCausalLM = None
    AutoTokenizer = None
    _TRANSFORMERS_VERSION = None


_MOONDREAM_MODEL = None
_MOONDREAM_TOKENIZER = None
_MOONDREAM_LOCK = threading.Lock()
_MOONDREAM_READY = threading.Event()
_MOONDREAM_LOADING = False
_MOONDREAM_LOADING_THREAD_ID: Optional[int] = None
_MOONDREAM_LOAD_ERROR: Optional[str] = None
_MODEL_DOWNLOAD_CALLBACK: Optional[Callable[[str], None]] = None  # Callback to show toast messages


def set_model_download_callback(callback: Optional[Callable[[str], None]]) -> None:
    """Set callback to display download/status messages.
    
    The callback receives a message string and should display it to the user
    (e.g., as a toast notification).
    """
    global _MODEL_DOWNLOAD_CALLBACK
    _MODEL_DOWNLOAD_CALLBACK = callback


def get_transformers_status() -> tuple[bool, Optional[str]]:
    """Return (available, version) for transformers."""
    return _TRANSFORMERS_AVAILABLE, _TRANSFORMERS_VERSION


def _is_model_cached() -> bool:
    """Check if Moondream2 model is already in HuggingFace cache."""
    try:
        from huggingface_hub import try_to_load_from_cache
        
        MODEL_ID = "vikhyatk/moondream2"
        # This returns the path if cached, None if not
        cached_path = try_to_load_from_cache(MODEL_ID, filename="model.safetensors")
        return cached_path is not None
    except Exception:
        # If we can't check, assume it might not be cached
        return False


def _load_moondream_model():
    """Lazily load the Moondream2 model."""
    global _MOONDREAM_MODEL, _MOONDREAM_TOKENIZER
    
    if _MOONDREAM_MODEL is not None:
        return _MOONDREAM_MODEL, _MOONDREAM_TOKENIZER
    
    logger = get_logger("Utilities")

    # If a background load is already running, wait for it to complete.
    if _MOONDREAM_LOADING and not _MOONDREAM_READY.is_set():
        if threading.get_ident() != _MOONDREAM_LOADING_THREAD_ID:
            logger.info("Moondream2 load in progress; waiting for model to be ready")
            _MOONDREAM_READY.wait()

    if _MOONDREAM_MODEL is not None:
        return _MOONDREAM_MODEL, _MOONDREAM_TOKENIZER
    
    # Check if transformers is available
    if not _TRANSFORMERS_AVAILABLE:
        logger.error("Transformers library not available at module import time")
        _MOONDREAM_READY.set()
        return None, None
    
    try:
        MODEL_ID = "vikhyatk/moondream2"
        
        # Check if model needs to be downloaded
        is_cached = _is_model_cached()
        if not is_cached:
            msg = "Downloading Moondream2 model (3.5GB)... This happens only on first run."
            logger.info(msg)
            if _MODEL_DOWNLOAD_CALLBACK:
                _MODEL_DOWNLOAD_CALLBACK(msg)
        
        # Log CUDA availability and memory before load (best-effort)
        try:
            import torch
            cuda_available = torch.cuda.is_available()
            logger.info("Moondream2 torch.cuda.is_available(): %s", cuda_available)
            if cuda_available:
                try:
                    free_bytes, total_bytes = torch.cuda.mem_get_info()
                    logger.info(
                        "Moondream2 CUDA memory free/total: %.2f GB / %.2f GB",
                        free_bytes / (1024 ** 3),
                        total_bytes / (1024 ** 3),
                    )
                except Exception as exc:
                    logger.warning("Moondream2 CUDA mem_get_info failed: %s", exc)
        except Exception as exc:
            logger.warning("Moondream2 torch import failed: %s", exc)

        logger.info("Loading Moondream2 model for screenshot analysis...")
        
        _MOONDREAM_MODEL = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            trust_remote_code=True,
            device_map="auto"  # Auto-select GPU if available, fallback to CPU
        )
        try:
            device_map = getattr(_MOONDREAM_MODEL, "hf_device_map", None)
            if device_map:
                logger.info("Moondream2 device map: %s", device_map)
            else:
                logger.info("Moondream2 device: %s", getattr(_MOONDREAM_MODEL, "device", "unknown"))
        except Exception as exc:
            logger.warning("Moondream2 device info unavailable: %s", exc)
        _MOONDREAM_TOKENIZER = AutoTokenizer.from_pretrained(MODEL_ID)
        logger.info("Moondream2 tokenizer loaded successfully")
        
        logger.info("Moondream2 model loaded successfully")
        if _MODEL_DOWNLOAD_CALLBACK:
            _MODEL_DOWNLOAD_CALLBACK("Moondream2 model loaded successfully")

        _MOONDREAM_READY.set()
        
        return _MOONDREAM_MODEL, _MOONDREAM_TOKENIZER
    except Exception as exc:
        logger.error("Failed to load Moondream2 model: %s", exc)
        _MOONDREAM_READY.set()
        return None, None


def start_moondream_background_load() -> None:
    """Start background load of transformers + Moondream2 model if not already loaded."""
    global _MOONDREAM_LOADING, _MOONDREAM_LOADING_THREAD_ID, _MOONDREAM_LOAD_ERROR
    if _MOONDREAM_MODEL is not None:
        _MOONDREAM_READY.set()
        return
    if _MOONDREAM_LOADING:
        return

    logger = get_logger("Utilities")
    logger.info(
        "Transformers availability: %s%s",
        _TRANSFORMERS_AVAILABLE,
        f" (version {_TRANSFORMERS_VERSION})" if _TRANSFORMERS_AVAILABLE else "",
    )
    _MOONDREAM_LOADING = True
    _MOONDREAM_LOAD_ERROR = None

    def _worker() -> None:
        global _MOONDREAM_LOADING, _MOONDREAM_LOADING_THREAD_ID, _MOONDREAM_LOAD_ERROR
        _MOONDREAM_LOADING_THREAD_ID = threading.get_ident()
        try:
            logger.info("Background Moondream2 preload started")
            model, tokenizer = _load_moondream_model()
            if model is None or tokenizer is None:
                _MOONDREAM_LOAD_ERROR = "Moondream2 model load failed"
                logger.warning("Background Moondream2 preload failed")
            else:
                logger.info("Background Moondream2 preload complete")
        finally:
            _MOONDREAM_LOADING = False
            _MOONDREAM_LOADING_THREAD_ID = None
            _MOONDREAM_READY.set()

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


class Utilities:
    @staticmethod
    def log_screenshot(log_file: Path, widget: Optional[QtWidgets.QWidget] = None) -> tuple[Optional[Path], Optional[threading.Thread]]:
        """Capture screenshot and start description generation.
        
        Returns:
            Tuple of (screenshot_path, description_thread). The caller should wait for
            the thread to complete before exiting to ensure description generation finishes.
        """
        logger = get_logger("Utilities")
        try:
            screen = QtWidgets.QApplication.primaryScreen()
            if screen is None:
                logger.error("No primary screen available for screenshot")
                return None, None

            base_name = log_file.stem
            target_dir = log_file.parent

            index = 1
            while True:
                candidate = target_dir / f"{base_name} ({index}).png"
                if not candidate.exists():
                    break
                index += 1

            window_id = 0
            if widget is not None:
                try:
                    window_id = int(widget.winId())
                except Exception:
                    window_id = 0
            pixmap = screen.grabWindow(window_id)
            if pixmap.isNull():
                logger.error("Screenshot capture returned empty pixmap")
                return None, None

            saved = pixmap.save(str(candidate), "PNG")
            if not saved:
                logger.error("Failed to save screenshot to %s", candidate)
                return None, None

            logger.info("Screenshot saved: %s", candidate)
            
            # Generate description in background thread (non-daemon so it completes before exit)
            thread = threading.Thread(
                target=Utilities._generate_screenshot_description,
                args=(candidate,),
                daemon=False
            )
            thread.start()
            
            return candidate, thread
        except Exception as exc:  # pragma: no cover
            logger.exception("Screenshot capture failed: %s", exc)
            return None, None

    @staticmethod
    def _generate_screenshot_description(image_path: Path) -> None:
        """Generate a description of the screenshot and save it as a .txt file."""
        logger = get_logger("Utilities")
        logger.info("[THREAD START] Screenshot description thread started for: %s", image_path)
        try:
            logger.info("Starting screenshot description generation for: %s", image_path)
            
            script_path = Path(__file__).resolve().parent.parent / "lab_describe_snapshot.py"
            if not script_path.exists():
                logger.error("Snapshot analyzer not found: %s", script_path)
                return

            cmd = [sys.executable, str(script_path), str(image_path)]
            env = os.environ.copy()
            env.setdefault("PYTHONIOENCODING", "utf-8")
            logger.info("Launching snapshot analyzer process: %s", " ".join(cmd))
            result = subprocess.run(cmd, capture_output=True, text=True, env=env)
            if result.stdout:
                logger.info("Snapshot analyzer stdout:\n%s", result.stdout)
            if result.stderr:
                logger.warning("Snapshot analyzer stderr:\n%s", result.stderr)
            if result.returncode != 0:
                logger.error("Snapshot analyzer exited with code %s", result.returncode)
                return

            description_path = image_path.with_suffix(".txt")
            if description_path.exists():
                logger.info("Screenshot description saved: %s", description_path)
            else:
                logger.warning("Snapshot analyzer completed but output not found: %s", description_path)
        except Exception as exc:
            logger.exception("Failed to generate screenshot description: %s", exc)

from __future__ import annotations

import base64
import json
import mimetypes
import os
import subprocess
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

from logger import get_logger
from constants import (
    DEFAULT_MODEL_FILE,
    DEFAULT_MMPROJ_FILE,
    GGUF_MODELS_DIR,
    LLAMA_SERVER_EXE,
    LLAMA_SERVER_HOST,
    LLAMA_SERVER_PORT,
)


@dataclass
class ModelInfo:
    name: str
    folder: str


_callbacks: List[Callable[[list[ModelInfo], Optional[str]], None]] = []
_state_callbacks: List[Callable[[str, Optional[str]], None]] = []
_logger = get_logger("LlamaCppServer")
_discover_thread_started = False
_state_thread_started = False
_cached_models: list[ModelInfo] | None = None
_cached_loaded_model: Optional[str] = None
_cached_state: Optional[tuple[str, Optional[str]]] = None


def is_running() -> bool:
    """Return True if llama-server responds to /health (200 or 503)."""
    url = f"http://{LLAMA_SERVER_HOST}:{LLAMA_SERVER_PORT}/health"
    try:
        _logger.info("Checking llama-server health: %s", url)
        with urllib.request.urlopen(url, timeout=1.5) as response:
            if response.status in (200, 503):
                _logger.info("llama-server health responded with %s", response.status)
                return True
            body = response.read().decode("utf-8")
            try:
                data = json.loads(body)
                ok = data.get("status") == "ok" or data.get("error") is not None
                _logger.info("llama-server health JSON ok=%s", ok)
                return ok
            except json.JSONDecodeError:
                _logger.info("llama-server health returned non-JSON response")
                return False
    except urllib.error.HTTPError as err:
        _logger.info("llama-server health HTTPError: %s", err.code)
        return err.code == 503
    except Exception as exc:
        _logger.info("llama-server health check failed: %s", exc)
        return False


def launch_server() -> Optional[subprocess.Popen]:
    """Launch llama-server if not running. Returns process or None on failure."""
    try:
        _logger.info(
            "Launching llama-server: %s -m %s --mmproj %s --host %s --port %s",
            LLAMA_SERVER_EXE,
            DEFAULT_MODEL_FILE,
            DEFAULT_MMPROJ_FILE,
            LLAMA_SERVER_HOST,
            LLAMA_SERVER_PORT,
        )
        return subprocess.Popen(
            [
                LLAMA_SERVER_EXE,
                "-m",
                DEFAULT_MODEL_FILE,
                "--mmproj",
                DEFAULT_MMPROJ_FILE,
                "--host",
                LLAMA_SERVER_HOST,
                "--port",
                str(LLAMA_SERVER_PORT),
            ]
        )
    except Exception as exc:
        _logger.exception("Failed to launch llama-server: %s", exc)
        return None


def ensure_running() -> bool:
    _logger.info("Ensure llama-server running")
    if is_running():
        _logger.info("llama-server already running")
        return True
    _logger.info("llama-server not running; launching")
    process = launch_server()
    if process is None:
        _logger.info("llama-server launch failed")
        return False
    _logger.info("llama-server launch process started")
    return True


def register_models_callback(callback: Callable[[list[ModelInfo], Optional[str]], None]) -> None:
    _logger.info("Registering models callback")
    _callbacks.append(callback)
    if _cached_models is not None:
        _logger.info("Using cached models for new callback")
        try:
            callback(_cached_models, _cached_loaded_model)
        except Exception:
            pass
    discover_models_async()


def discover_models_async() -> None:
    global _discover_thread_started
    if _discover_thread_started:
        return
    _discover_thread_started = True
    thread = threading.Thread(target=_discover_and_notify, daemon=True)
    thread.start()


def register_model_state_callback(callback: Callable[[str, Optional[str]], None]) -> None:
    _logger.info("Registering model state callback")
    _state_callbacks.append(callback)
    if _cached_state is not None:
        try:
            callback(_cached_state[0], _cached_state[1])
        except Exception:
            pass
    start_model_state_watch()


def start_model_state_watch(interval_seconds: float = 2.0) -> None:
    global _state_thread_started
    if _state_thread_started:
        _logger.info("Model state watch already started")
        return
    _state_thread_started = True
    _logger.info("Starting model state watch")
    ensure_running()
    thread = threading.Thread(
        target=_poll_model_state,
        args=(interval_seconds,),
        daemon=True,
    )
    thread.start()


def _discover_and_notify() -> None:
    global _cached_models, _cached_loaded_model
    models = _discover_models()
    loaded = _fetch_loaded_model()
    _cached_models = models
    _cached_loaded_model = loaded
    for callback in _callbacks:
        try:
            callback(models, loaded)
        except Exception:
            continue


def _poll_model_state(interval_seconds: float) -> None:
    global _cached_state
    state, model_name = _get_model_state()
    _cached_state = (state, model_name)
    for callback in _state_callbacks:
        try:
            callback(state, model_name)
        except Exception:
            continue


def _discover_models() -> list[ModelInfo]:
    results: list[ModelInfo] = []
    for root, _, files in os.walk(GGUF_MODELS_DIR):
        for file in files:
            if not file.lower().endswith(".gguf"):
                continue
            if "mmproj" in file.lower():
                continue
            name = os.path.splitext(file)[0]
            results.append(ModelInfo(name=name, folder=root))
    return results


def _fetch_loaded_model() -> Optional[str]:
    global _cached_loaded_model
    urls = [
        f"http://{LLAMA_SERVER_HOST}:{LLAMA_SERVER_PORT}/v1/models",
        f"http://{LLAMA_SERVER_HOST}:{LLAMA_SERVER_PORT}/models",
    ]
    for url in urls:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                data = json.loads(response.read().decode("utf-8"))
            if isinstance(data, dict):
                if "data" in data and isinstance(data["data"], list) and data["data"]:
                    _cached_loaded_model = data["data"][0].get("id")
                    return _cached_loaded_model
                if "models" in data and isinstance(data["models"], list) and data["models"]:
                    _cached_loaded_model = data["models"][0].get("id")
                    return _cached_loaded_model
        except Exception:
            continue
    return _cached_loaded_model


def _get_model_state() -> tuple[str, Optional[str]]:
    url = f"http://{LLAMA_SERVER_HOST}:{LLAMA_SERVER_PORT}/health"
    try:
        with urllib.request.urlopen(url, timeout=1.5) as response:
            status = response.status
            if status == 200:
                return "Ready", _fetch_loaded_model()
            if status == 503:
                return "Loading", _fetch_loaded_model()
    except urllib.error.HTTPError as err:
        if err.code == 503:
            return "Loading", _fetch_loaded_model()
    except Exception:
        pass
    return "None", None


def load_model(model_name: str) -> None:
    """Load a model via router API (POST /models/load). Raises on failure."""
    ensure_running()
    url = f"http://{LLAMA_SERVER_HOST}:{LLAMA_SERVER_PORT}/models/load"
    payload = json.dumps({"model": model_name}).encode("utf-8")
    request = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    _logger.info("Requesting model load: %s", model_name)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            if response.status != 200:
                raise RuntimeError(f"Model load failed: HTTP {response.status} {body}")
            data = json.loads(body) if body else {}
            if not data.get("success", False):
                raise RuntimeError(f"Model load failed: {data}")
    except Exception as exc:
        _logger.exception("Model load request failed: %s", exc)
        raise


class LlamaCppChatServer:
    def __init__(self, host: str = LLAMA_SERVER_HOST, port: int = LLAMA_SERVER_PORT) -> None:
        self._logger = None
        self._host = host
        self._port = port
        self._messages: list[dict] = []
        self._stream_callbacks: list[Callable[[str], None]] = []
        self._lock = threading.Lock()

    @property
    def messages(self) -> list[dict]:
        return list(self._messages)

    def register_stream_callback(self, callback: Callable[[str], None]) -> None:
        self._stream_callbacks.append(callback)

    def clear_messages(self) -> None:
        with self._lock:
            self._messages.clear()

    def send_message(self, text: str, image_paths: Optional[list[Path]] = None) -> None:
        ensure_running()
        content = self._build_content(text, image_paths or [])
        user_message = {"role": "user", "content": content}
        assistant_message = {"role": "assistant", "content": ""}

        with self._lock:
            self._messages.append(user_message)
            self._messages.append(assistant_message)

        thread = threading.Thread(
            target=self._stream_completion,
            args=(assistant_message,),
            daemon=True,
        )
        thread.start()

    def _stream_completion(self, assistant_message: dict) -> None:
        url = f"http://{self._host}:{self._port}/v1/chat/completions"
        model_name = _fetch_loaded_model() or "default"
        payload = {
            "model": model_name,
            "messages": self.messages,
            "stream": True,
        }
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

        try:
            with urllib.request.urlopen(request, timeout=120) as response:
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
                    delta = self._extract_delta(payload)
                    if not delta:
                        continue
                    with self._lock:
                        assistant_message["content"] += delta
                    self._emit_stream_chunk(delta)
        except Exception:
            return

    def _emit_stream_chunk(self, chunk: str) -> None:
        for callback in self._stream_callbacks:
            try:
                callback(chunk)
            except Exception:
                continue

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

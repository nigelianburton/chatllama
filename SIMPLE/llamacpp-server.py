from __future__ import annotations

import base64
import json
import mimetypes
import os
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import sys
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
    SETTINGS_DEV,
    SETTINGS_HOME,
    SETTINGS_WORK,
)


@dataclass
class ModelInfo:
    name: str
    folder: str


_callbacks: List[Callable[[list[ModelInfo], Optional[str]], None]] = []
_state_callbacks: List[Callable[[str, Optional[str]], None]] = []
_cache_callbacks: List[Callable[[str], None]] = []
_logger = get_logger("LlamaCppServer")
_discover_thread_started = False
_state_thread_started = False
_cached_models: list[ModelInfo] | None = None
_cached_loaded_model: Optional[str] = None
_cached_state: Optional[tuple[str, Optional[str]]] = None
_settings_data: dict | None = None
_settings_path: Path | None = None
_models_preset_path: Path | None = None
_active_model: Optional[str] = None


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
        preset_path = _get_models_preset_path()
        _logger.info(
            "Launching llama-server (router): %s --models-preset %s --host %s --port %s",
            LLAMA_SERVER_EXE,
            preset_path,
            LLAMA_SERVER_HOST,
            LLAMA_SERVER_PORT,
        )
        return subprocess.Popen(
            [
                LLAMA_SERVER_EXE,
                "--models-preset",
                str(preset_path),
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
        if not is_router_mode():
            _logger.info("llama-server running in non-router mode; restarting")
            stop_server()
        else:
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


def register_cache_warm_callback(callback: Callable[[str], None]) -> None:
    _logger.info("Registering cache warm callback")
    _cache_callbacks.append(callback)


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
    global _cached_models, _cached_loaded_model, _active_model
    ensure_running()
    models = _fetch_models_from_server()
    loaded = _fetch_loaded_model()
    _cached_models = models
    _cached_loaded_model = loaded
    if loaded:
        _active_model = loaded
    _ensure_default_model_loaded(models)
    _backfill_model_cache_async(models)
    generate_models_preset_async(_discover_models())
    for callback in _callbacks:
        try:
            callback(models, loaded)
        except Exception:
            continue


def _poll_model_state(interval_seconds: float) -> None:
    global _cached_state
    while True:
        state, model_name = _get_model_state()
        _cached_state = (state, model_name)
        for callback in _state_callbacks:
            try:
                callback(state, model_name)
            except Exception:
                continue
        try:
            threading.Event().wait(interval_seconds)
        except Exception:
            pass


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


def get_discovered_models() -> list[ModelInfo]:
    return _discover_models()


def is_router_mode() -> bool:
    status, data = _get_models_response()
    return status == 200 and isinstance(data.get("data"), list)


def stop_server() -> None:
    if sys.platform == "win32":
        subprocess.run(
            [
                "powershell",
                "-Command",
                "Get-Process llama-server -ErrorAction SilentlyContinue | Stop-Process -Force",
            ],
            check=False,
        )
    else:
        subprocess.run(["pkill", "-f", "llama-server"], check=False)


def _get_models_response() -> tuple[int, dict]:
    url = f"http://{LLAMA_SERVER_HOST}:{LLAMA_SERVER_PORT}/models"
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            body = response.read().decode("utf-8")
        return 200, json.loads(body) if body else {}
    except urllib.error.HTTPError as err:
        try:
            body = err.read().decode("utf-8")
            return err.code, json.loads(body) if body else {}
        except Exception:
            return err.code, {}
    except Exception:
        return 0, {}


def _fetch_models_from_server() -> list[ModelInfo]:
    status, data = _get_models_response()
    if status != 200:
        return []
    results: list[ModelInfo] = []
    for item in data.get("data", []):
        model_id = item.get("id") or ""
        if "mmproj" in model_id.lower():
            continue
        path = item.get("path") or ""
        folder = str(Path(path).parent) if path else ""
        name = model_id or Path(path).stem
        results.append(ModelInfo(name=name, folder=folder))
    return results


def _fetch_loaded_model() -> Optional[str]:
    global _cached_loaded_model
    if _active_model:
        return _active_model
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
    if _active_model:
        state = _get_active_model_status()
        return state, _active_model
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


def _get_active_model_status() -> str:
    status, data = _get_models_response()
    if status != 200:
        return "Unknown"
    target = (_active_model or "").lower()
    for item in data.get("data", []):
        model_id = (item.get("id") or "").lower()
        if model_id != target:
            continue
        value = (item.get("status") or {}).get("value") or ""
        value = value.lower()
        if value in ("loaded", "ready"):
            return "Ready"
        if value in ("loading", "initializing"):
            return "Loading"
        if value:
            return value.capitalize()
    return "Unknown"


def get_current_model_settings() -> dict:
    """Return cached settings for the current model, refreshing chat_template if missing."""
    model_name = _fetch_loaded_model()
    if not model_name:
        return {}
    settings = _load_settings()
    model_cache = settings.setdefault("model_cache", {})
    entry = model_cache.setdefault(model_name, {})
    props = None
    if not entry.get("chat_template") or "modalities" not in entry or "context_length" not in entry:
        props = _fetch_props(model_name)
        chat_template = props.get("chat_template") if props else None
        if chat_template:
            entry["chat_template"] = chat_template
        if props and "modalities" in props:
            entry["modalities"] = props.get("modalities")
        if props:
            gen = props.get("default_generation_settings") or {}
            entry.setdefault("context_length", gen.get("n_ctx", 16384))
            entry.setdefault("temperature", gen.get("temperature", 0.8))
            entry.setdefault("max_response_length", gen.get("n_predict", 0))
        else:
            entry.setdefault("context_length", 16384)
            entry.setdefault("temperature", 0.8)
            entry.setdefault("max_response_length", 0)
        _save_settings(settings)
    else:
        entry.setdefault("context_length", 16384)
        entry.setdefault("temperature", 0.8)
        entry.setdefault("max_response_length", 0)
    return entry


def load_model(model_name: str) -> None:
    """Load a model via router API (POST /models/load). Raises on failure."""
    global _active_model
    ensure_running()
    _active_model = model_name
    url = f"http://{LLAMA_SERVER_HOST}:{LLAMA_SERVER_PORT}/models/load"
    payload = json.dumps({"model": model_name}).encode("utf-8")
    request = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    _logger.info("Requesting model load: %s", model_name)
    for attempt in range(2):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8")
                if response.status != 200:
                    raise RuntimeError(f"Model load failed: HTTP {response.status} {body}")
                data = json.loads(body) if body else {}
                if not data.get("success", False):
                    raise RuntimeError(f"Model load failed: {data}")
            get_current_model_settings()
            _update_default_model(model_name)
            _refresh_model_state(_get_active_model_status())
            return
        except urllib.error.HTTPError as err:
            body = err.read().decode("utf-8")
            try:
                data = json.loads(body) if body else {}
            except json.JSONDecodeError:
                data = {}
            message = (data.get("error") or {}).get("message") or ""
            lower_message = message.lower()
            if err.code == 400 and "already loaded" in lower_message:
                _logger.info("Model already loaded: %s", model_name)
                get_current_model_settings()
                _update_default_model(model_name)
                _refresh_model_state(_get_active_model_status())
                return
            if err.code == 500 and "mmproj" in lower_message and attempt == 0:
                _logger.info("mmproj missing; restarting router and retrying load")
                _restart_router_with_preset()
                continue
            _logger.exception("Model load request failed: HTTP %s %s", err.code, body)
            raise
        except Exception as exc:
            _logger.exception("Model load request failed: %s", exc)
            raise


def _refresh_model_state(state: str) -> None:
    global _cached_state, _cached_loaded_model
    loaded = _fetch_loaded_model()
    _cached_loaded_model = loaded
    _cached_state = (state, loaded)
    for callback in _state_callbacks:
        try:
            callback(state, loaded)
        except Exception:
            continue


def _update_default_model(model_name: str) -> None:
    if not model_name:
        return
    settings = _load_settings()
    settings["default_model"] = model_name
    _save_settings(settings)


def _backfill_model_cache_async(models: list[ModelInfo]) -> None:
    names = [model.name for model in models if model.name]

    def _worker() -> None:
        _notify_cache_warm("start")
        _backfill_model_cache(names)
        _notify_cache_warm("end")

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


def _notify_cache_warm(state: str) -> None:
    for callback in _cache_callbacks:
        try:
            callback(state)
        except Exception:
            continue


def _backfill_model_cache(model_names: list[str]) -> None:
    settings = _load_settings()
    model_cache = settings.setdefault("model_cache", {})
    updated = False

    def _ensure_entry(name: str) -> None:
        nonlocal updated
        entry = model_cache.setdefault(name, {})
        if entry.get("chat_template") and "modalities" in entry and "context_length" in entry:
            return
        props = _fetch_props(name)
        chat_template = props.get("chat_template") if props else None
        if chat_template:
            entry["chat_template"] = chat_template
            updated = True
        if props and "modalities" in props:
            entry["modalities"] = props.get("modalities")
            updated = True
        gen = (props.get("default_generation_settings") or {}) if props else {}
        if "context_length" not in entry:
            entry["context_length"] = gen.get("n_ctx", 16384)
            updated = True
        if "temperature" not in entry:
            entry["temperature"] = gen.get("temperature", 0.8)
            updated = True
        if "max_response_length" not in entry:
            entry["max_response_length"] = gen.get("n_predict", 0)
            updated = True

    for name in model_names:
        if not name:
            continue
        _ensure_entry(name)

    for name in list(model_cache.keys()):
        if not name:
            continue
        _ensure_entry(name)

    if updated:
        _save_settings(settings)


def _ensure_default_model_loaded(models: list[ModelInfo]) -> None:
    settings = _load_settings()
    default_model = settings.get("default_model")
    if not default_model:
        return
    if _active_model and _active_model == default_model:
        return
    candidate = default_model
    if any(sep in default_model for sep in ("/", "\\", ":")):
        candidate = Path(default_model).stem
    model_names = {model.name for model in models if model.name}
    model_ref = candidate if candidate in model_names else default_model
    try:
        load_model(model_ref)
    except Exception:
        _logger.info("Default model load failed for %s", model_ref)


def _load_settings() -> dict:
    global _settings_data, _settings_path
    if _settings_data is not None and _settings_path is not None:
        return _settings_data

    candidates = [
        Path(SETTINGS_DEV) / "simple_llama_settings.json",
        Path(SETTINGS_WORK) / "simple_llama_settings.json",
        Path(SETTINGS_HOME) / "simple_llama_settings.json",
    ]
    for path in candidates:
        if path.exists():
            _settings_path = path
            break
    if _settings_path is None:
        _settings_path = candidates[0]
        _settings_path.parent.mkdir(parents=True, exist_ok=True)
        _settings_data = {
            "settings_folder": str(_settings_path.parent),
            "default_model": DEFAULT_MODEL_FILE,
            "model_cache": {},
        }
        _save_settings(_settings_data)
        return _settings_data

    try:
        _settings_data = json.loads(_settings_path.read_text())
    except Exception:
        _settings_data = {}

    _settings_data.setdefault("settings_folder", str(_settings_path.parent))
    _settings_data.setdefault("default_model", DEFAULT_MODEL_FILE)
    _settings_data.setdefault("model_cache", {})
    return _settings_data


def _save_settings(settings: dict) -> None:
    if _settings_path is None:
        return
    try:
        _settings_path.write_text(json.dumps(settings, indent=2))
    except Exception as exc:
        _logger.warning("Failed to write settings cache: %s", exc)


def generate_models_preset_async(models: list[ModelInfo]) -> Path:
    preset_path = _get_models_preset_path()

    def _worker() -> None:
        _write_models_preset(preset_path, models)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    return preset_path


def _get_models_preset_path() -> Path:
    global _models_preset_path
    if _models_preset_path is not None:
        return _models_preset_path
    settings = _load_settings()
    settings_folder = Path(settings.get("settings_folder", SETTINGS_DEV))
    _models_preset_path = settings_folder / "models_preset.ini"
    return _models_preset_path


def _restart_router_with_preset() -> None:
    stop_server()
    generate_models_preset_async(_discover_models())
    launch_server()
    _wait_for_health()


def _wait_for_health(timeout_seconds: float = 60.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if is_running():
            return True
        time.sleep(0.5)
    return False


def _write_models_preset(preset_path: Path, models: list[ModelInfo]) -> None:
    try:
        lines: list[str] = ["version = 1", "", "[*]", "", ""]
        seen: set[str] = set()
        for model in models:
            name = model.name
            if not name:
                continue
            section = name
            if section in seen:
                continue
            seen.add(section)
            model_path = Path(model.folder) / f"{name}.gguf"
            if not model_path.exists():
                model_path = Path(model.folder) / name
            lines.append(f"[{section}]")
            lines.append(f"model = {model_path}")
            mmproj_path = _find_mmproj_path(Path(model.folder), name)
            if mmproj_path:
                lines.append(f"mmproj = {mmproj_path}")
            lines.append("")
        preset_path.parent.mkdir(parents=True, exist_ok=True)
        preset_path.write_text("\n".join(lines))
        _logger.info("Wrote models preset: %s", preset_path)
    except Exception as exc:
        _logger.warning("Failed to write models preset: %s", exc)


def _find_mmproj_path(folder: Path, model_name: str) -> Optional[Path]:
    if not folder.exists():
        return None
    candidates = sorted(folder.glob("*.mmproj*.gguf"))
    if not candidates:
        return None
    lowered = model_name.lower()
    for candidate in candidates:
        if lowered in candidate.name.lower():
            return candidate
    return candidates[0]


def _fetch_chat_template(model_name: Optional[str]) -> Optional[str]:
    if not model_name:
        return None
    query = urllib.parse.quote(model_name)
    url = f"http://{LLAMA_SERVER_HOST}:{LLAMA_SERVER_PORT}/props?model={query}"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data.get("chat_template")
    except Exception:
        return None


def _fetch_props(model_name: Optional[str]) -> dict:
    if not model_name:
        return {}
    query = urllib.parse.quote(model_name)
    url = f"http://{LLAMA_SERVER_HOST}:{LLAMA_SERVER_PORT}/props?model={query}"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return {}


class LlamaCppChatServer:
    def __init__(self, host: str = LLAMA_SERVER_HOST, port: int = LLAMA_SERVER_PORT) -> None:
        self._logger = get_logger(self)
        self._host = host
        self._port = port
        self._messages: list[dict] = []
        self._stream_callbacks: list[Callable[[str], None]] = []
        self._lock = threading.Lock()
        self._stream_log_buffer = ""

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
        self._logger.info("User: %s", text)
        self._stream_log_buffer = ""
        if image_paths:
            for path in image_paths:
                self._logger.info("User attachment: %s", path)
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
        for attempt in range(2):
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
                        self._log_stream_delta(delta)
                        self._emit_stream_chunk(delta)
                self._flush_stream_log()
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
                self._logger.error("Chat stream failed: %s", exc)
                self._flush_stream_log()
                return

    def _emit_stream_chunk(self, chunk: str) -> None:
        for callback in self._stream_callbacks:
            try:
                callback(chunk)
            except Exception:
                continue

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

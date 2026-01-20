from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from SIMPLE.constants import (
    DEFAULT_MODEL_FILE,
    DEFAULT_MMPROJ_FILE,
    GGUF_MODELS_DIR,
    LLAMA_SERVER_EXE,
    LLAMA_SERVER_HOST,
    LLAMA_SERVER_PORT,
)

ROUTER_MODELS_DIR = GGUF_MODELS_DIR


def _url(path: str) -> str:
    return f"http://{LLAMA_SERVER_HOST}:{LLAMA_SERVER_PORT}{path}"


def http_get(path: str, timeout: float = 5.0) -> tuple[int, str]:
    req = urllib.request.Request(_url(path), method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as err:
        return err.code, err.read().decode("utf-8")
    except Exception as exc:
        return 0, f"{type(exc).__name__}: {exc}"


def http_post(path: str, payload: dict, timeout: float = 10.0) -> tuple[int, str]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        _url(path),
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as err:
        return err.code, err.read().decode("utf-8")
    except Exception as exc:
        return 0, f"{type(exc).__name__}: {exc}"


def stop_server() -> None:
    if os.name == "nt":
        subprocess.run(
            ["powershell", "-Command", "Get-Process llama-server -ErrorAction SilentlyContinue | Stop-Process -Force"],
            check=False,
        )
    else:
        subprocess.run(["pkill", "-f", "llama-server"], check=False)


def start_router() -> subprocess.Popen:
    preset_path = ensure_models_preset()
    return subprocess.Popen(
        [
            LLAMA_SERVER_EXE,
            "--host",
            LLAMA_SERVER_HOST,
            "--port",
            str(LLAMA_SERVER_PORT),
            "--models-preset",
            str(preset_path),
        ]
    )


def start_model(model_path: str) -> subprocess.Popen:
    return subprocess.Popen(
        [
            LLAMA_SERVER_EXE,
            "-m",
            model_path,
            "--mmproj",
            DEFAULT_MMPROJ_FILE,
            "--host",
            LLAMA_SERVER_HOST,
            "--port",
            str(LLAMA_SERVER_PORT),
        ]
    )


def wait_health(timeout: float = 60.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        status, _ = http_get("/health", timeout=2.0)
        if status in (200, 503):
            return True
        time.sleep(0.5)
    return False


def wait_ready(timeout: float = 180.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        status, _ = http_get("/health", timeout=2.0)
        if status == 200:
            return True
        time.sleep(1.0)
    return False


def ensure_models_preset() -> Path:
    module_path = Path(__file__).resolve().parents[1] / "SIMPLE" / "llamacpp-server.py"
    simple_root = module_path.parent
    if str(simple_root) not in sys.path:
        sys.path.insert(0, str(simple_root))
    spec = importlib.util.spec_from_file_location("llamacpp_server", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load llamacpp-server module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    models = module.get_discovered_models()
    preset_path = module.generate_models_preset_async(models)
    deadline = time.time() + 5
    while time.time() < deadline:
        if preset_path.exists() and preset_path.stat().st_size > 0:
            break
        time.sleep(0.1)
    return preset_path


def pick_model_id(data: dict) -> str | None:
    items = data.get("data") or []
    target = Path(DEFAULT_MODEL_FILE).name
    for item in items:
        model_id = item.get("id") or ""
        if target in model_id:
            return model_id
        path = item.get("path") or ""
        if target in path:
            return model_id
    if items:
        return items[0].get("id")
    return None


def pick_two_models(data: dict) -> tuple[str | None, str | None]:
    items = data.get("data") or []
    filtered = [item for item in items if "mmproj" not in (item.get("id") or "").lower()]
    if len(filtered) >= 2:
        return filtered[0].get("id"), filtered[1].get("id")
    if len(filtered) == 1:
        return filtered[0].get("id"), None
    if len(items) >= 2:
        return items[0].get("id"), items[1].get("id")
    if len(items) == 1:
        return items[0].get("id"), None
    return None, None


def try_router_load() -> bool:
    status, body = http_get("/models", timeout=5.0)
    if status != 200:
        print(f"/models failed: HTTP {status} {body}")
        return False
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        print("/models returned invalid JSON")
        return False
    items = data.get("data") or []
    print(f"/models returned {len(items)} entries")
    if items:
        print("First 10 model ids:")
        for item in items[:10]:
            print(f"- {item.get('id')}")
    model_id, model_id_second = pick_two_models(data)
    if not model_id:
        print("No model id found from /models")
        return False
    print(f"Attempting /models/load with id: {model_id}")
    status, body = http_post("/models/load", {"model": model_id}, timeout=30.0)
    if status != 200:
        print(f"/models/load failed: HTTP {status} {body}")
        return False
    try:
        result = json.loads(body) if body else {}
    except json.JSONDecodeError:
        result = {}
    if not result.get("success", False):
        print(f"/models/load returned failure: {result}")
        return False
    if not model_id_second or model_id_second == model_id:
        print("No second model id available for reload test")
        return True
    print(f"Attempting /models/load with second id: {model_id_second}")
    status, body = http_post("/models/load", {"model": model_id_second}, timeout=30.0)
    if status != 200:
        print(f"/models/load (second) failed: HTTP {status} {body}")
        return False
    try:
        result = json.loads(body) if body else {}
    except json.JSONDecodeError:
        result = {}
    if not result.get("success", False):
        print(f"/models/load (second) returned failure: {result}")
        return False
    return True


def main() -> int:
    print("Checking existing server...")
    if not wait_health(timeout=5.0):
        print("Server not reachable; starting router mode...")
        stop_server()
        start_router()
        if not wait_health(timeout=60.0):
            print("Router mode failed to start")
            return 1

    if try_router_load():
        print("Router model load succeeded")
        return 0

    print("Router mode failed; restarting router mode and retrying...")
    stop_server()
    start_router()
    if not wait_health(timeout=60.0):
        print("Router restart failed")
        return 1

    if try_router_load():
        print("Router model load succeeded after restart")
        return 0

    print("Router mode appears broken; starting server with explicit model")
    stop_server()
    start_model(DEFAULT_MODEL_FILE)
    if not wait_health(timeout=120.0):
        print("Direct model start failed")
        return 1

    if not wait_ready(timeout=180.0):
        print("Model did not become ready in time")
        return 1

    status, body = http_get("/v1/models", timeout=5.0)
    print(f"/v1/models status: HTTP {status} {body}")
    return 0 if status == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())

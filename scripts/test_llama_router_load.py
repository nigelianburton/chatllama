from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from SIMPLE.constants import (
    DEFAULT_MODEL_FILE,
    DEFAULT_MMPROJ_FILE,
    LLAMA_SERVER_EXE,
    LLAMA_SERVER_HOST,
    LLAMA_SERVER_PORT,
)

ROUTER_MODELS_DIR = str(Path(DEFAULT_MODEL_FILE).parent)


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
    return subprocess.Popen(
        [
            LLAMA_SERVER_EXE,
            "--host",
            LLAMA_SERVER_HOST,
            "--port",
            str(LLAMA_SERVER_PORT),
            "--models-dir",
            ROUTER_MODELS_DIR,
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
    model_id = pick_model_id(data)
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

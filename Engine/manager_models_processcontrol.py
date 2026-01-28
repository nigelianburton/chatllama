from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from typing import Optional

from Engine.logger import get_logger
from Engine.manager_models_settings import get_models_preset_path
from constants import LLAMA_SERVER_EXE, LLAMA_SERVER_HOST, LLAMA_SERVER_PORT


_logger = get_logger("LlamaCppServer")
_launch_lock = threading.Lock()
_launch_in_progress = False


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
        preset_path = get_models_preset_path()
        _logger.info(
            "Launching llama-server (router): %s --models-preset %s --host %s --port %s",
            LLAMA_SERVER_EXE,
            preset_path,
            LLAMA_SERVER_HOST,
            LLAMA_SERVER_PORT,
        )
        process = subprocess.Popen(
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
        _logger.info("llama-server launch started (pid=%s)", process.pid)
        return process
    except Exception as exc:
        _logger.exception("Failed to launch llama-server: %s", exc)
        return None


def ensure_running() -> bool:
    _logger.info("Ensure llama-server running")
    if not _ensure_single_llama_process():
        return False
    if is_running():
        if not is_router_mode():
            _logger.info("llama-server running in non-router mode; restarting")
            stop_server()
        else:
            _logger.info("llama-server already running")
            return True
    with _launch_lock:
        global _launch_in_progress
        if _launch_in_progress:
            _logger.warning("llama-server launch already in progress; skipping duplicate launch")
            return wait_for_health()
        _launch_in_progress = True
    _logger.info("llama-server not running; launching")
    process = launch_server()
    if process is None:
        _logger.info("llama-server launch failed")
        with _launch_lock:
            _launch_in_progress = False
        return False
    _logger.info("llama-server launch process started")
    if wait_for_health():
        with _launch_lock:
            _launch_in_progress = False
        return True
    _logger.info("llama-server failed to become healthy after launch")
    with _launch_lock:
        _launch_in_progress = False
    return False


def get_models_response() -> tuple[int, dict]:
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


def is_router_mode() -> bool:
    status, data = get_models_response()
    return status == 200 and isinstance(data.get("data"), list)


def stop_server() -> None:
    if sys.platform == "win32":
        pids = _get_llama_server_pids()
        if pids:
            _logger.info("Stopping llama-server processes (pids=%s)", ", ".join(pids))
        else:
            _logger.info("Stopping llama-server processes (none found)")
    else:
        _logger.info("Stopping llama-server processes")
    if sys.platform == "win32":
        result = subprocess.run(
            [
                "powershell",
                "-Command",
                "Get-Process llama-server -ErrorAction SilentlyContinue | Stop-Process -Force",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.stdout:
            _logger.info("llama-server stop stdout: %s", result.stdout.strip())
        if result.stderr:
            _logger.warning("llama-server stop stderr: %s", result.stderr.strip())
    else:
        result = subprocess.run(["pkill", "-f", "llama-server"], check=False, capture_output=True, text=True)
        if result.stdout:
            _logger.info("llama-server stop stdout: %s", result.stdout.strip())
        if result.stderr:
            _logger.warning("llama-server stop stderr: %s", result.stderr.strip())


def wait_for_health(timeout_seconds: float = 60.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if is_running():
            return True
        time.sleep(0.5)
    return False


def _get_llama_server_pids() -> list[str]:
    if sys.platform != "win32":
        return []
    try:
        output = subprocess.check_output(
            [
                "powershell",
                "-Command",
                "Get-Process -Name llama-server -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id",
            ],
            text=True,
        )
    except Exception:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


def _ensure_single_llama_process() -> bool:
    if sys.platform != "win32":
        return True
    pids = _get_llama_server_pids()
    if not pids:
        _logger.info("llama-server discovery: no running processes found")
        return True
    if len(pids) == 1:
        _logger.info("llama-server discovery: one running process found (pid=%s)", pids[0])
        return True
    _logger.warning("llama-server discovery: %s running processes found (pids=%s)", len(pids), ", ".join(pids))
    try:
        from PyQt6 import QtCore, QtWidgets
    except Exception:
        _logger.warning("PyQt unavailable; stopping all llama-server processes")
        stop_server()
        return True
    app = QtWidgets.QApplication.instance()
    if app is None:
        _logger.warning("No QApplication; stopping all llama-server processes")
        stop_server()
        return True

    def _show_dialog() -> QtWidgets.QMessageBox.StandardButton:
        message = QtWidgets.QMessageBox()
        message.setWindowTitle("Error")
        message.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        message.setText(f"Error {len(pids)} llama-servers are running.")
        message.setInformativeText("Stop them ?")
        message.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        message.setStandardButtons(
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )
        message.setStyleSheet("QLabel { color: #000000; }")
        return QtWidgets.QMessageBox.StandardButton(message.exec())

    if QtCore.QThread.currentThread() != app.thread():
        result_box: dict[str, QtWidgets.QMessageBox.StandardButton | None] = {"result": None}

        class _DialogRunner(QtCore.QObject):
            @QtCore.pyqtSlot()
            def run(self) -> None:
                result_box["result"] = _show_dialog()

        runner = _DialogRunner()
        runner.moveToThread(app.thread())
        QtCore.QMetaObject.invokeMethod(
            runner,
            "run",
            QtCore.Qt.ConnectionType.BlockingQueuedConnection,
        )
        result = result_box["result"] or QtWidgets.QMessageBox.StandardButton.No
    else:
        result = _show_dialog()
    if result == QtWidgets.QMessageBox.StandardButton.Yes:
        _logger.info("User chose to stop multiple llama-server processes")
        stop_server()
        remaining = _get_llama_server_pids()
        if remaining:
            _logger.error(
                "llama-server processes still running after stop request (count=%s, pids=%s)",
                len(remaining),
                ", ".join(remaining),
            )
            return False
        _logger.info("llama-server processes cleared after stop request")
        return True
    _logger.info("User chose not to stop multiple llama-server processes; exiting app")
    app.quit()
    return False

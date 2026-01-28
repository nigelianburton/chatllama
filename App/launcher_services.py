from __future__ import annotations

import ctypes
import json
import os
import socket
import subprocess
import sys
from pathlib import Path
from typing import Callable

SINGLE_INSTANCE_MUTEX = "ChatLlamaSingleInstance"
SINGLE_INSTANCE_HOST = "127.0.0.1"
SINGLE_INSTANCE_PORT = 38621
_SINGLE_INSTANCE_HANDLE: int | None = None


def start_control_service(logger) -> subprocess.Popen | None:
    service_path = Path(__file__).resolve().parents[1] / "Engine" / "control_service.py"
    logger.info("Starting control service: %s", service_path)
    try:
        repo_root = Path(__file__).resolve().parents[1]
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (
            f"{pythonpath}{os.pathsep}{repo_root}" if pythonpath else str(repo_root)
        )
        return subprocess.Popen([sys.executable, str(service_path)], cwd=str(repo_root), env=env)
    except Exception as exc:
        logger.error("Failed to start control service: %s", exc)
        return None


def stop_control_service(logger, control_process: subprocess.Popen | None) -> None:
    if control_process is None:
        return
    if control_process.poll() is not None:
        return
    logger.info("Stopping control service (pid=%s)", control_process.pid)
    control_process.terminate()
    try:
        control_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        logger.warning("Control service did not exit; killing")
        control_process.kill()


def send_args_to_instance(logger, argv: list[str]) -> bool:
    payload = json.dumps({"argv": argv}).encode("utf-8")
    try:
        with socket.create_connection((SINGLE_INSTANCE_HOST, SINGLE_INSTANCE_PORT), timeout=2.0) as sock:
            sock.sendall(payload)
        logger.info("Single-instance: sent args to running instance: %s", " ".join(argv))
        return True
    except Exception as exc:
        logger.error("Single-instance: failed to send args: %s", exc)
        return False


def start_ipc_listener(logger, on_args: Callable[[list[str]], None]) -> None:
    def _run() -> None:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind((SINGLE_INSTANCE_HOST, SINGLE_INSTANCE_PORT))
            server.listen(5)
        except Exception as exc:
            logger.error("Single-instance: IPC bind failed: %s", exc)
            return
        while True:
            try:
                client, _ = server.accept()
            except Exception:
                continue
            with client:
                data = b""
                while True:
                    chunk = client.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                if not data:
                    continue
                try:
                    payload = json.loads(data.decode("utf-8"))
                except Exception as exc:
                    logger.error("Single-instance: invalid IPC payload: %s", exc)
                    continue
                argv = payload.get("argv") if isinstance(payload, dict) else None
                if not isinstance(argv, list):
                    continue
                logger.info("Single-instance: received args: %s", " ".join(str(a) for a in argv))
                on_args([str(a) for a in argv])

    import threading

    threading.Thread(target=_run, daemon=True).start()


def acquire_single_instance(logger, argv: list[str]) -> bool:
    if sys.platform.startswith("win"):
        global _SINGLE_INSTANCE_HANDLE
        mutex = ctypes.windll.kernel32.CreateMutexW(None, False, SINGLE_INSTANCE_MUTEX)
        already_running = ctypes.windll.kernel32.GetLastError() == 183
        if already_running:
            send_args_to_instance(logger, argv)
            return False
        _SINGLE_INSTANCE_HANDLE = int(mutex)
        logger.info("Single-instance: mutex acquired")
        return True
    try:
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_sock.bind((SINGLE_INSTANCE_HOST, SINGLE_INSTANCE_PORT))
        test_sock.close()
        logger.info("Single-instance: lock acquired")
        return True
    except Exception:
        send_args_to_instance(logger, argv)
        return False

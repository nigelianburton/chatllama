from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
import unittest


def _is_port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


def _start_control_service() -> subprocess.Popen | None:
    if _is_port_open("127.0.0.1", 8001):
        return None
    env = os.environ.copy()
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env["PYTHONPATH"] = repo_root
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "Engine.control_service:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8001",
        ],
        cwd=repo_root,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _stop_control_service(process: subprocess.Popen | None) -> None:
    if process is None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PepperReflex parity tests")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run the Reflex parity tests",
    )
    args = parser.parse_args()

    if not args.test:
        print("Nothing to do. Use --test to run the Reflex parity tests.")
        return 1

    control_process = _start_control_service()
    if control_process is not None:
        time.sleep(1.5)

    try:
        loader = unittest.TestLoader()
        suite = loader.discover("tests", pattern="reflex_parity_tests.py")
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        return 0 if result.wasSuccessful() else 1
    finally:
        _stop_control_service(control_process)


if __name__ == "__main__":
    sys.exit(main())

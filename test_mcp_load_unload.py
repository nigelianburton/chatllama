from __future__ import annotations

import argparse
import asyncio
import importlib.util
import socket
import subprocess
import sys
import time
from pathlib import Path

HOST = "127.0.0.1"
PORT = 6820
URL = f"http://{HOST}:{PORT}/mcp"
ROOT = Path(__file__).resolve().parent
FASHION_HTTP = ROOT / "MCP_Local" / "fashion_http.py"


def patch_sse_writer() -> bool:
    """Swallow ClosedResourceError when SSE stream closes during shutdown."""
    try:
        from mcp.server import streamable_http
        from anyio import ClosedResourceError
    except Exception:
        return False

    original = getattr(streamable_http, "standalone_sse_writer", None)
    if original is None:
        return False

    if getattr(streamable_http, "_chatllama_patched", False):
        return True

    async def _wrapped(*args, **kwargs):
        try:
            return await original(*args, **kwargs)
        except ClosedResourceError:
            return None

    streamable_http.standalone_sse_writer = _wrapped
    streamable_http._chatllama_patched = True
    return True


def run_server() -> None:
    patch_sse_writer()

    if not FASHION_HTTP.exists():
        raise FileNotFoundError(f"MCP file not found: {FASHION_HTTP}")

    spec = importlib.util.spec_from_file_location("fashion_http", FASHION_HTTP)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load fashion_http module")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    server = getattr(module, "server", None)
    if server is None:
        raise RuntimeError("fashion_http.py did not expose `server`")

    server.run(transport="http", host=HOST, port=PORT)


def wait_for_port(host: str, port: int, timeout: float = 5.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            if sock.connect_ex((host, port)) == 0:
                return
        time.sleep(0.1)
    raise TimeoutError(f"Server did not open {host}:{port} within {timeout}s")


async def load_tools() -> int:
    from fastmcp import Client

    async with Client(URL) as client:
        tools = await client.list_tools()
        return len(tools)


def start_server_subprocess() -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, __file__, "--server"],
        cwd=str(ROOT),
    )


def stop_server_subprocess(process: subprocess.Popen) -> None:
    process.terminate()
    try:
        process.wait(5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(5)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", action="store_true")
    args = parser.parse_args()

    if args.server:
        run_server()
        return 0

    server_process = start_server_subprocess()
    try:
        wait_for_port(HOST, PORT, timeout=10.0)
        tool_count = asyncio.run(load_tools())
        print(f"Loaded MCP tools: {tool_count}")
    finally:
        stop_server_subprocess(server_process)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

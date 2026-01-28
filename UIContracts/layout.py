from __future__ import annotations

from pathlib import Path
from typing import Callable, Protocol, runtime_checkable


@runtime_checkable
class UILayout(Protocol):
    def create_app(self, argv: list[str]):
        ...

    def create_window(self, exit_idle: bool, log_file: Path, settings_folder: Path):
        ...

    def show_window(self, window) -> None:
        ...

    def register_about_to_quit(self, app, callback: Callable[[], None]) -> None:
        ...

    def capture_screenshot(self, window):
        ...

    def invoke_ui(self, window, func: Callable[[], object]) -> object:
        ...

    def autorun_stage_message(self, window, text: str, image_paths: list[Path]) -> None:
        ...

    def autorun_submit_message(self, window) -> None:
        ...

    def register_availability_callback(self, window, callback: Callable[[str], None]) -> bool:
        ...

    def get_last_assistant_message(self, window) -> str:
        ...

    def schedule_exit(self, window, delay_ms: int) -> None:
        ...

    def get_mcp_hooks(self, window):
        ...

    def refresh_mcp_tools(self, window) -> None:
        ...


def validate_layout(module) -> None:
    required = [
        "create_app",
        "create_window",
        "show_window",
        "register_about_to_quit",
        "capture_screenshot",
        "invoke_ui",
        "autorun_stage_message",
        "autorun_submit_message",
        "register_availability_callback",
        "get_last_assistant_message",
        "schedule_exit",
        "get_mcp_hooks",
        "refresh_mcp_tools",
    ]
    missing = [name for name in required if not callable(getattr(module, name, None))]
    if missing:
        raise RuntimeError(f"UI layout missing required callables: {', '.join(missing)}")

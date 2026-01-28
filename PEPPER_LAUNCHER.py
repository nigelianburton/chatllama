from __future__ import annotations

import argparse
import atexit
import importlib.util
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable

from App.autorun_orchestrator import start_autorun
from App.launcher_services import (
    acquire_single_instance,
    start_control_service,
    start_ipc_listener,
    stop_control_service,
)
from App.mcp_service import start_internal_mcp
from Engine.interaction_logger import init_interaction_logger
from Engine.logger import configure_logging, get_logger
from constants import SETTINGS_DEV, SETTINGS_HOME, SETTINGS_WORK
from UIContracts.layout import validate_layout

class LayoutModule:
    def __init__(self, module) -> None:
        self._module = module

    def create_app(self, argv: list[str]):
        return self._module.create_app(argv)

    def create_window(self, exit_idle: bool, log_file: Path, settings_folder: Path):
        return self._module.create_window(exit_idle, log_file, settings_folder)

    def show_window(self, window) -> None:
        return self._module.show_window(window)

    def register_about_to_quit(self, app, callback: Callable[[], None]) -> None:
        self._module.register_about_to_quit(app, callback)

    def capture_screenshot(self, window):
        return self._module.capture_screenshot(window)

    def invoke_ui(self, window, func: Callable[[], object]) -> object:
        return self._module.invoke_ui(window, func)

    def autorun_stage_message(self, window, text: str, image_paths: list[Path]) -> None:
        self._module.autorun_stage_message(window, text, image_paths)

    def autorun_submit_message(self, window) -> None:
        self._module.autorun_submit_message(window)

    def register_availability_callback(self, window, callback: Callable[[str], None]) -> bool:
        return bool(self._module.register_availability_callback(window, callback))

    def get_last_assistant_message(self, window) -> str:
        return str(self._module.get_last_assistant_message(window) or "")

    def schedule_exit(self, window, delay_ms: int) -> None:
        self._module.schedule_exit(window, delay_ms)

    def get_mcp_hooks(self, window):
        return self._module.get_mcp_hooks(window)

    def refresh_mcp_tools(self, window) -> None:
        self._module.refresh_mcp_tools(window)


def _load_layout_module(ui_name: str) -> LayoutModule:
    ui_key = ui_name.strip().lower()
    ui_map = {
        "qt": ("pepper_qt_layout", Path(__file__).resolve().parent / "UI" / "pepper_qt_layout.py"),
    }
    if ui_key not in ui_map:
        raise RuntimeError(f"Unknown UI '{ui_name}'. Available: {', '.join(ui_map)}")
    module_name, layout_path = ui_map[ui_key]
    spec = importlib.util.spec_from_file_location(module_name, layout_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load layout module from {layout_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    validate_layout(module)
    return LayoutModule(module)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ChatLlama SIMPLE")
    parser.add_argument(
        "--autorun",
        nargs="*",
        help="Run autorun instructions from a JSON file or inline text (optionally followed by image paths).",
    )
    parser.add_argument(
        "--home",
        action="store_true",
        help=f"Use home settings folder ({SETTINGS_HOME}).",
    )
    parser.add_argument(
        "--work",
        action="store_true",
        help=f"Use work settings folder ({SETTINGS_WORK}).",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help=f"Use dev settings folder ({SETTINGS_DEV}).",
    )
    parser.add_argument(
        "--ui",
        default="qt",
        help="UI backend to use (default: qt).",
    )
    return parser


def _autorun_looks_like_file(value: str) -> bool:
    value = value.strip()
    if not value:
        return False
    path = Path(value)
    if path.exists():
        return True
    if path.drive:
        return True
    if path.suffix:
        return True
    if any(sep in value for sep in ("/", "\\")):
        return True
    return False


def _materialize_autorun_text(settings_folder: Path, text: str) -> Path:
    target_dir = settings_folder / "autoruns"
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "autorun_text_" + stamp
    target_path = target_dir / f"{safe_name}.json"
    payload = {"messages": [{"text": text}]}
    target_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target_path


def _normalize_autorun_args(
    autorun_args: list[str] | None,
    settings_folder: Path,
    logger,
) -> tuple[list[str] | None, bool]:
    if autorun_args is None:
        return None, False
    if len(autorun_args) != 1:
        return autorun_args, False
    candidate = autorun_args[0]
    if _autorun_looks_like_file(candidate):
        return autorun_args, False
    target_path = _materialize_autorun_text(settings_folder, candidate)
    logger.info("Autorun text wrapped into %s", target_path)
    return [str(target_path)], True


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()

    settings_folder = Path(SETTINGS_DEV)
    if args.home:
        settings_folder = Path(SETTINGS_HOME)
    if args.work:
        settings_folder = Path(SETTINGS_WORK)
    if args.dev:
        settings_folder = Path(SETTINGS_DEV)

    config = configure_logging(settings_folder)
    logger = get_logger("Main")
    logger.info("Log file: %s", config.log_file)
    logger.info("Python: %s", sys.executable)
    logger.info("Conda env: %s", os.environ.get("CONDA_PREFIX", "(not set)"))
    init_interaction_logger(config.log_file)

    if not acquire_single_instance(logger, sys.argv[1:]):
        logger.info("Single-instance: exiting secondary instance")
        return

    control_process = start_control_service(logger)
    atexit.register(stop_control_service, logger, control_process)

    autorun_args, autorun_inline = _normalize_autorun_args(args.autorun, settings_folder, logger)

    layout = _load_layout_module(args.ui)
    app = layout.create_app(sys.argv)
    internal_mcp_server = None

    def _on_app_quit() -> None:
        if internal_mcp_server:
            internal_mcp_server.stop()
        stop_control_service(logger, control_process)

    layout.register_about_to_quit(app, _on_app_quit)
    window = layout.create_window(
        exit_idle=(autorun_args is not None),
        log_file=config.log_file,
        settings_folder=settings_folder,
    )
    layout.show_window(window)

    internal_mcp_server = start_internal_mcp(layout, window, logger)

    def _handle_forwarded_args(argv: list[str]) -> None:
        forwarded = parser.parse_args(argv)
        forwarded_autorun, forwarded_inline = _normalize_autorun_args(
            forwarded.autorun,
            settings_folder,
            logger,
        )
        if forwarded_autorun is not None:
            logger.info("Single-instance: processing forwarded autorun")
            start_autorun(
                layout,
                window,
                logger,
                forwarded_autorun,
                log_final_response=forwarded_inline,
            )

    start_ipc_listener(logger, _handle_forwarded_args)

    if autorun_args is not None:
        start_autorun(
            layout,
            window,
            logger,
            autorun_args,
            log_final_response=autorun_inline,
        )

    sys.exit(app.exec())

if __name__ == "__main__":
    main()

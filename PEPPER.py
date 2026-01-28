from __future__ import annotations

import argparse
import atexit
import ctypes
import json
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Dict

from PyQt6 import QtCore, QtGui, QtWidgets

from Engine.logger import configure_logging, get_logger
from Engine.autorun import run_autorun
from Engine.interaction_logger import init_interaction_logger
from App.mcp_service import start_internal_mcp
from App.status_controller import StatusMessageController, attach_download_callback
from App.window_controller import ExitIdleController
from App.window_state_controller import WindowStateController
from UI.page_main import MainPageWidget
from MCP_Internal.card_svg import SVGCard
from constants import SETTINGS_DEV, SETTINGS_HOME, SETTINGS_WORK

SINGLE_INSTANCE_MUTEX = "ChatLlamaSingleInstance"
SINGLE_INSTANCE_HOST = "127.0.0.1"
SINGLE_INSTANCE_PORT = 38621
_SINGLE_INSTANCE_HANDLE: int | None = None


class UiBridge(QtCore.QObject):
    def __init__(self) -> None:
        super().__init__()
        self.last_result: object | None = None

    @QtCore.pyqtSlot(object)
    def invoke(self, func: Callable[[], object]) -> None:
        self.last_result = func()


class _LegacyLayoutAdapter:
    def invoke_ui(self, window, func: Callable[[], object]) -> object:
        return window._invoke_ui(func)

    def get_mcp_hooks(self, window):
        return window._invoke_ui, window._create_svg_card, window._delete_svg_card

    def refresh_mcp_tools(self, window) -> None:
        window._chat_container.refresh_mcp_tools()


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ChatLlama SIMPLE")
    parser.add_argument(
        "--autorun",
        nargs="*",
        help="Run autorun instructions from a text file (optionally followed by image paths).",
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
    return parser


def _send_args_to_instance(logger, argv: list[str]) -> bool:
    payload = json.dumps({"argv": argv}).encode("utf-8")
    try:
        with socket.create_connection((SINGLE_INSTANCE_HOST, SINGLE_INSTANCE_PORT), timeout=2.0) as sock:
            sock.sendall(payload)
        logger.info("Single-instance: sent args to running instance: %s", " ".join(argv))
        return True
    except Exception as exc:
        logger.error("Single-instance: failed to send args: %s", exc)
        return False


def _start_ipc_listener(logger, on_args: Callable[[list[str]], None]) -> None:
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

    threading.Thread(target=_run, daemon=True).start()


def _acquire_single_instance(logger, argv: list[str]) -> bool:
    if sys.platform.startswith("win"):
        global _SINGLE_INSTANCE_HANDLE
        mutex = ctypes.windll.kernel32.CreateMutexW(None, False, SINGLE_INSTANCE_MUTEX)
        already_running = ctypes.windll.kernel32.GetLastError() == 183
        if already_running:
            _send_args_to_instance(logger, argv)
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
        _send_args_to_instance(logger, argv)
        return False


class ChatLlamaWindow(QtWidgets.QMainWindow):
    def __init__(self, exit_idle: bool, log_file: Path, settings_folder: Path) -> None:
        super().__init__()
        self._logger = get_logger(self)
        self._mcp_server: object | None = None
        self._exit_idle = exit_idle
        self._log_file = log_file
        self._cards: Dict[str, SVGCard] = {}
        self._ui_bridge = UiBridge()
        self._layout_adapter = _LegacyLayoutAdapter()
        self._exit_controller = ExitIdleController(
            log_file=self._log_file,
            schedule_timer=lambda delay_ms, func: QtCore.QTimer.singleShot(delay_ms, func),
            quit_app=self._quit_app,
            get_widget=lambda: self,
            get_cards=lambda: list(self._cards.values()),
            logger=self._logger,
        )

        self.setWindowTitle("ChatLlama - SIMPLE")
        self.resize(1200, 800)

        self._page = MainPageWidget(settings_folder)
        self.setCentralWidget(self._page)

        self._model_title = self._page.model_title_label
        self._status_text = self._page.status_label
        self._progress = self._page.progress_bar
        self._status_controller = StatusMessageController(
            get_text=self._model_title.text,
            set_text=self._model_title.setText,
            schedule_timer=lambda delay_ms, func: QtCore.QTimer.singleShot(delay_ms, func),
            logger=self._logger,
        )
        self._state_controller = WindowStateController(
            set_model_title=self._model_title.setText,
            set_progress_range=self._progress.setRange,
            set_progress_value=self._progress.setValue,
            set_header_color=self._set_column_header_color,
            logger=self._logger,
        )

        self._settings_container = self._page.settings_container
        self._settings_container.model_state_updated.connect(self._state_controller.on_model_state_updated)
        self._settings_container.model_load_started.connect(self._state_controller.on_model_load_started)
        self._settings_container.model_load_finished.connect(self._state_controller.on_model_load_finished)
        self._settings_container.cache_warm_started.connect(self._state_controller.on_cache_warm_started)
        self._settings_container.cache_warm_finished.connect(self._state_controller.on_cache_warm_finished)
        self._settings_container.model_changed.connect(self._state_controller.on_model_changed)

        self._chat_container = self._page.chat_container
        self._settings_container.mcp_settings_changed.connect(self._chat_container.refresh_mcp_tools)
        self._chat_container.model_state_updated.connect(self._state_controller.on_model_state_updated)

        self._cards_container = self._page.cards_container
        self._cards_layout = self._page.cards_layout
        
        # Register callback for Moondream2 model download messages
        attach_download_callback(self._status_controller, duration_ms=5000)

    def _set_column_header_color(self, name: str, color: str) -> None:
        self._page.set_column_header_color(name, color)

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        QtCore.QTimer.singleShot(0, self._start_mcp_server)
        # Pre-load Moondream2 model in background thread if autorun is enabled
        # This ensures the model is ready when we need it for screenshot description at exit
        if self._exit_idle:
            QtCore.QTimer.singleShot(100, self._preload_moondream2)
    
    def _preload_moondream2(self) -> None:
        """Pre-load Moondream2 model in background thread for autorun screenshot descriptions."""
        self._logger.info(
            "Skipping in-process Moondream2 preload; external snapshot analyzer will be used"
        )

    def _start_mcp_server(self) -> None:
        if self._mcp_server is None:
            try:
                self._mcp_server = start_internal_mcp(self._layout_adapter, self, self._logger)
            except Exception as exc:
                self._logger.exception("Failed to start internal MCP server: %s", exc)

        # Do not auto-exit when autorun is enabled; exit is triggered after autorun completion

    def _exit_if_idle(self) -> None:
        self._exit_controller.request_exit()

    def _quit_app(self) -> None:
        self._stop_mcp_server()
        app = QtWidgets.QApplication.instance()
        if app:
            app.quit()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self._stop_mcp_server()
        super().closeEvent(event)

    def _stop_mcp_server(self) -> None:
        server = self._mcp_server
        if server is None:
            return
        stop = getattr(server, "stop", None)
        if callable(stop):
            try:
                stop()
            except Exception as exc:
                self._logger.warning("Failed to stop internal MCP server: %s", exc)

    def schedule_exit(self, delay_ms: int) -> None:
        self._logger.info("Scheduling exit in %d ms", delay_ms)
        QtCore.QTimer.singleShot(delay_ms, self._exit_if_idle)

    def _invoke_ui(self, func: Callable[[], object]) -> object:
        self._ui_bridge.last_result = None
        return QtCore.QMetaObject.invokeMethod(
            self._ui_bridge,
            "invoke",
            QtCore.Qt.ConnectionType.BlockingQueuedConnection,
            QtCore.Q_ARG(object, func),
        ) or self._ui_bridge.last_result

    def _create_svg_card(self, guid: str, is_portrait: bool) -> SVGCard:
        card = SVGCard(guid=guid, is_portrait=is_portrait)
        self._cards[guid] = card
        self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)
        return card

    def _delete_svg_card(self, card: SVGCard) -> None:
        guid = card.guid
        self._cards_layout.removeWidget(card)
        card.deleteLater()
        self._cards.pop(guid, None)


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

    if not _acquire_single_instance(logger, sys.argv[1:]):
        logger.info("Single-instance: exiting secondary instance")
        return

    control_process: subprocess.Popen | None = None

    def _start_control_service() -> None:
        nonlocal control_process
        if control_process is not None and control_process.poll() is None:
            return
        service_path = Path(__file__).resolve().parent / "Engine" / "control_service.py"
        logger.info("Starting control service: %s", service_path)
        control_process = subprocess.Popen([sys.executable, str(service_path)])

    def _stop_control_service() -> None:
        nonlocal control_process
        if control_process is None:
            return
        if control_process.poll() is not None:
            control_process = None
            return
        logger.info("Stopping control service (pid=%s)", control_process.pid)
        control_process.terminate()
        try:
            control_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning("Control service did not exit; killing")
            control_process.kill()
        control_process = None

    _start_control_service()
    atexit.register(_stop_control_service)

    app = QtWidgets.QApplication(sys.argv)
    app.aboutToQuit.connect(_stop_control_service)
    window = ChatLlamaWindow(
        exit_idle=(args.autorun is not None),  # Set exit_idle=True if autorun is requested
        log_file=config.log_file,
        settings_folder=settings_folder,
    )
    window.show()
    def _start_autorun(autorun_args: list[str]) -> None:
        if not autorun_args:
            return

        def _finish(success: bool, message: str) -> None:
            delay_ms = 1000
            if success:
                logger.info("Autorun completion signaled; waiting %d ms then capturing screenshot and exiting", delay_ms)
            else:
                logger.error("Autorun failed: %s", message)
            # Always capture screenshot/description before exit so agents can see state
            window._invoke_ui(lambda: window.schedule_exit(delay_ms))

        def _run() -> None:
            def _stage(text: str, image_paths: list[Path]) -> None:
                def _do() -> None:
                    window._chat_container.autorun_stage_message(text, image_paths)
                window._invoke_ui(_do)

            def _submit() -> None:
                def _do() -> None:
                    window._chat_container.autorun_submit_message()
                window._invoke_ui(_do)

            def _register_availability(callback: Callable[[str], None]) -> bool:
                def _do() -> bool:
                    return window._chat_container.register_availability_callback(callback)
                result = window._invoke_ui(_do)
                return bool(result)

            def _get_last_response() -> str:
                def _do() -> str:
                    return window._chat_container.get_last_assistant_message()
                result = window._invoke_ui(_do)
                return str(result or "")

            success, message = run_autorun(
                autorun_args,
                ui_stage_message=_stage,
                ui_submit_message=_submit,
                register_availability_callback=_register_availability,
                ui_get_last_response=_get_last_response,
            )
            _finish(success, message)

        threading.Thread(target=_run, daemon=True).start()

    def _handle_forwarded_args(argv: list[str]) -> None:
        forwarded = parser.parse_args(argv)
        if forwarded.autorun is not None:
            logger.info("Single-instance: processing forwarded autorun")
            _start_autorun(forwarded.autorun)

    _start_ipc_listener(logger, _handle_forwarded_args)

    if args.autorun is not None:
        _start_autorun(args.autorun)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()



from __future__ import annotations

import argparse
import ctypes
import json
import os
import socket
import sys
import threading
from pathlib import Path
from typing import Callable, Dict, Optional

from PyQt6 import QtCore, QtGui, QtWidgets

from Engine.logger import configure_logging, get_logger
from Engine.mcp_internal_server import InternalMcpServer
from Engine.autorun import run_autorun
from Engine.interaction_logger import init_interaction_logger
from Engine.utilities import Utilities
from UI.column_chat import ChatColumnWidget
from UI.column_cards import ColumnCardsWidget
from UI.column_settings import ColumnSettingsWidget
from MCP_Internal.svg_card import SVGCard
from constants import (
    HEADER_COLOR_FAULT,
    HEADER_COLOR_LOADING,
    HEADER_COLOR_READY,
    SETTINGS_DEV,
    SETTINGS_HOME,
    SETTINGS_WORK,
    TOGGLE_OFF_COLOR,
    TOGGLE_ON_COLOR,
)

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


class ColumnPanel(QtWidgets.QFrame):
    def __init__(
        self,
        title: str,
        color: str,
        content_widget: Optional[QtWidgets.QWidget] = None,
        header_color: Optional[str] = None,
    ) -> None:
        super().__init__()
        self._logger = get_logger(self)

        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"background-color: {color};")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._toolbar = QtWidgets.QToolBar()
        self._toolbar.setIconSize(QtCore.QSize(16, 16))
        self._toolbar.setMovable(False)
        self._toolbar.setStyleSheet(f"background-color: {header_color or color};")

        title_label = QtWidgets.QLabel(title)
        title_label.setStyleSheet("font-weight: bold; padding: 4px;")

        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)

        self._toolbar.addWidget(title_label)
        self._toolbar.addWidget(spacer)

        layout.addWidget(self._toolbar)

        if content_widget is None:
            content = QtWidgets.QLabel(f"{title} content")
            content.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            content_widget = content
        layout.addWidget(content_widget, 1)

    def set_header_color(self, color: str) -> None:
        self._toolbar.setStyleSheet(f"background-color: {color};")




class ChatLlamaWindow(QtWidgets.QMainWindow):
    def __init__(self, exit_idle: bool, log_file: Path, settings_folder: Path) -> None:
        super().__init__()
        self._logger = get_logger(self)
        self._mcp_server: InternalMcpServer | None = None
        self._exit_idle = exit_idle
        self._log_file = log_file
        self._cards: Dict[str, SVGCard] = {}
        self._ui_bridge = UiBridge()

        self.setWindowTitle("ChatLlama - SIMPLE")
        self.resize(1200, 800)

        self._central = QtWidgets.QWidget()
        self.setCentralWidget(self._central)

        main_layout = QtWidgets.QVBoxLayout(self._central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        top_toolbar = QtWidgets.QToolBar()
        top_toolbar.setMovable(False)
        self._model_title = QtWidgets.QLabel("Model: None")
        self._model_title.setStyleSheet("font-weight: bold;")
        top_toolbar.addWidget(self._model_title)

        toolbar_spacer = QtWidgets.QWidget()
        toolbar_spacer.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred
        )
        top_toolbar.addWidget(toolbar_spacer)

        self._status_text = QtWidgets.QLabel("50%")
        self._status_text.setFixedWidth(50)
        self._status_text.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self._status_text.setVisible(False)
        top_toolbar.addWidget(self._status_text)

        self._progress = QtWidgets.QProgressBar()
        self._progress.setFixedWidth(150)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        top_toolbar.addWidget(self._progress)
        self._top_toolbar = top_toolbar
        main_layout.addWidget(top_toolbar)

        self._toggle_style = (
            f"QToolButton {{ background: {TOGGLE_OFF_COLOR}; padding: 4px; }}"
            f"QToolButton:checked {{ background: {TOGGLE_ON_COLOR}; }}"
        )

        self._splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        main_layout.addWidget(self._splitter, 1)

        self._columns: Dict[str, QtWidgets.QWidget] = {}
        self._column_visible: Dict[str, bool] = {}
        self._toggle_buttons: Dict[str, QtWidgets.QToolButton] = {}

        self._settings_container = ColumnSettingsWidget(settings_folder)
        self._settings_container.model_state_updated.connect(self._on_model_state_updated)
        self._settings_container.model_load_started.connect(self._on_model_load_started)
        self._settings_container.model_load_finished.connect(self._on_model_load_finished)
        self._settings_container.cache_warm_started.connect(self._on_cache_warm_started)
        self._settings_container.cache_warm_finished.connect(self._on_cache_warm_finished)
        self._settings_container.model_changed.connect(self._on_model_changed)
        self._add_column("Settings", "#f7e0e0", content_widget=self._settings_container)
        self._chat_container = ChatColumnWidget()
        self._settings_container.mcp_settings_changed.connect(self._chat_container.refresh_mcp_tools)
        self._chat_container.model_state_updated.connect(self._on_model_state_updated)
        self._add_column("Chat", "#e0f7e0", content_widget=self._chat_container)
        self._cards_container = ColumnCardsWidget()
        self._cards_layout = self._cards_container.cards_layout
        self._add_column("Cards", "#e0e8f7", content_widget=self._cards_container)

        self._apply_splitter_sizes()

    def _on_model_load_started(self) -> None:
        self._progress.setRange(0, 0)
        self._progress.setValue(0)

    def _on_model_load_finished(self, success: bool) -> None:
        self._progress.setRange(0, 100)
        self._progress.setValue(0)

    def _on_model_changed(self, model_name: str) -> None:
        self._model_title.setText(f"Model: {model_name}" if model_name else "Model: None")

    def _on_cache_warm_started(self) -> None:
        self._progress.setRange(0, 0)
        self._progress.setValue(0)

    def _on_cache_warm_finished(self) -> None:
        self._progress.setRange(0, 100)
        self._progress.setValue(0)

    def _on_model_state_updated(self, state: str) -> None:
        settings_color, chat_color = self._get_header_colors_for_state(state)
        self._set_column_header_color("Settings", settings_color)
        self._set_column_header_color("Chat", chat_color)

    def _get_header_colors_for_state(self, state: str) -> tuple[str, str]:
        if state == "Ready":
            return HEADER_COLOR_READY, HEADER_COLOR_READY
        if state == "Waiting":
            return HEADER_COLOR_READY, HEADER_COLOR_LOADING
        if state == "Loading":
            return HEADER_COLOR_LOADING, HEADER_COLOR_LOADING
        if state == "Fault":
            return HEADER_COLOR_FAULT, HEADER_COLOR_FAULT
        return HEADER_COLOR_FAULT, HEADER_COLOR_FAULT

    def _set_column_header_color(self, name: str, color: str) -> None:
        panel = self._columns.get(name)
        if isinstance(panel, ColumnPanel):
            panel.set_header_color(color)

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        QtCore.QTimer.singleShot(0, self._start_mcp_server)

    def _add_column(
        self,
        name: str,
        color: str,
        content_widget: Optional[QtWidgets.QWidget] = None,
        header_color: Optional[str] = None,
    ) -> None:
        def on_toggle(checked: bool) -> None:
            self._column_visible[name] = checked
            widget = self._columns[name]
            widget.setVisible(checked)
            self._apply_splitter_sizes()

        panel = ColumnPanel(name, color, content_widget=content_widget, header_color=header_color)
        self._splitter.addWidget(panel)
        self._columns[name] = panel
        self._column_visible[name] = True

        toggle = QtWidgets.QToolButton()
        toggle.setText(name)
        toggle.setCheckable(True)
        toggle.setChecked(True)
        toggle.setStyleSheet(self._toggle_style)
        toggle.clicked.connect(lambda checked, n=name: on_toggle(checked))
        self._top_toolbar.addWidget(toggle)
        self._toggle_buttons[name] = toggle


    def _apply_splitter_sizes(self) -> None:
        visible = [name for name, is_on in self._column_visible.items() if is_on]
        if not visible:
            sizes = [0 for _ in self._columns]
        else:
            per = int(1000 / len(visible))
            sizes = [per if self._column_visible[name] else 0 for name in self._columns]
        self._splitter.setSizes(sizes)

    def _start_mcp_server(self) -> None:
        if self._mcp_server is None:
            try:
                self._logger.info("Starting internal MCP server...")
                self._mcp_server = InternalMcpServer(
                    ui_invoke=self._invoke_ui,
                    ui_create_card=self._create_svg_card,
                    ui_delete_card=self._delete_svg_card,
                )
                self._mcp_server.start()
                self._chat_container.refresh_mcp_tools()
            except Exception as exc:
                self._logger.exception("Failed to start internal MCP server: %s", exc)

        if self._exit_idle:
            QtCore.QTimer.singleShot(0, self._exit_if_idle)

    def _exit_if_idle(self) -> None:
        self._logger.info("Exit-idle requested; capturing screenshot and exiting")
        Utilities.log_screenshot(self._log_file, widget=self)
        app = QtWidgets.QApplication.instance()
        if app:
            app.quit()

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

    app = QtWidgets.QApplication(sys.argv)
    window = ChatLlamaWindow(
        exit_idle=False,
        log_file=config.log_file,
        settings_folder=settings_folder,
    )
    window.show()
    def _start_autorun(autorun_args: list[str]) -> None:
        if not autorun_args:
            return
        QtCore.QTimer.singleShot(0, lambda: window.schedule_exit(60000))

        def _finish(success: bool, message: str) -> None:
            if success:
                logger.info("Autorun completion signaled; scheduling exit")
                window._invoke_ui(lambda: window.schedule_exit(1000))
            else:
                logger.error(message)
                app = QtWidgets.QApplication.instance()
                if app:
                    app.quit()

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

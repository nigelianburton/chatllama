from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict

from PyQt6 import QtCore, QtGui, QtWidgets

from Engine.logger import get_logger
from App.window_controller import ExitIdleController
from App.status_controller import StatusMessageController, attach_download_callback
from App.window_state_controller import WindowStateController
from MCP_Internal.card_svg import SVGCard
from UI.page_main import MainPageWidget


class UiBridge(QtCore.QObject):
    def __init__(self) -> None:
        super().__init__()
        self.last_result: object | None = None

    @QtCore.pyqtSlot(object)
    def invoke(self, func: Callable[[], object]) -> None:
        self.last_result = func()


class ChatLlamaWindow(QtWidgets.QMainWindow):
    def __init__(
        self,
        exit_idle: bool,
        log_file: Path,
        settings_folder: Path,
    ) -> None:
        super().__init__()
        self._logger = get_logger(self)
        self._exit_idle = exit_idle
        self._log_file = log_file
        self._cards: Dict[str, SVGCard] = {}
        self._ui_bridge = UiBridge()
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

        attach_download_callback(self._status_controller, duration_ms=5000)

    def _set_column_header_color(self, name: str, color: str) -> None:
        self._page.set_column_header_color(name, color)

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        if self._exit_idle:
            QtCore.QTimer.singleShot(100, self._preload_moondream2)

    def _preload_moondream2(self) -> None:
        self._logger.info(
            "Skipping in-process Moondream2 preload; external snapshot analyzer will be used"
        )

    def _exit_if_idle(self) -> None:
        self._exit_controller.request_exit()

    def _quit_app(self) -> None:
        app = QtWidgets.QApplication.instance()
        if app:
            app.quit()

    def schedule_exit(self, delay_ms: int) -> None:
        self._logger.info("Scheduling exit in %d ms", delay_ms)
        QtCore.QTimer.singleShot(delay_ms, self._exit_if_idle)

    def capture_screenshot(self):
        return self._exit_controller.capture_screenshot()

    def _invoke_ui(self, func: Callable[[], object]) -> object:
        if QtCore.QThread.currentThread() == self.thread():
            return func()
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


def create_app(argv: list[str]):
    return QtWidgets.QApplication(argv)


def register_about_to_quit(app, callback: Callable[[], None]) -> None:
    app.aboutToQuit.connect(callback)


def create_window(exit_idle: bool, log_file: Path, settings_folder: Path):
    return ChatLlamaWindow(exit_idle, log_file, settings_folder)


def show_window(window: ChatLlamaWindow) -> None:
    window.show()


def capture_screenshot(window: ChatLlamaWindow):
    return window.capture_screenshot()


def start_autorun(window: ChatLlamaWindow, logger, autorun_args: list[str] | None) -> None:
    if not autorun_args:
        return
    logger.warning("start_autorun is deprecated in layout; use launcher orchestration")


def invoke_ui(window: ChatLlamaWindow, func: Callable[[], object]) -> object:
    return window._invoke_ui(func)


def autorun_stage_message(window: ChatLlamaWindow, text: str, image_paths: list[Path]) -> None:
    def _do() -> None:
        window._chat_container.autorun_stage_message(text, image_paths)
    window._invoke_ui(_do)


def autorun_submit_message(window: ChatLlamaWindow) -> None:
    def _do() -> None:
        window._chat_container.autorun_submit_message()
    window._invoke_ui(_do)


def register_availability_callback(window: ChatLlamaWindow, callback: Callable[[str], None]) -> bool:
    def _do() -> bool:
        return window._chat_container.register_availability_callback(callback)
    result = window._invoke_ui(_do)
    return bool(result)


def get_last_assistant_message(window: ChatLlamaWindow) -> str:
    def _do() -> str:
        return window._chat_container.get_last_assistant_message()
    result = window._invoke_ui(_do)
    return str(result or "")


def schedule_exit(window: ChatLlamaWindow, delay_ms: int) -> None:
    window.schedule_exit(delay_ms)


def get_mcp_hooks(window: ChatLlamaWindow):
    return window._invoke_ui, window._create_svg_card, window._delete_svg_card


def refresh_mcp_tools(window: ChatLlamaWindow) -> None:
    def _do() -> None:
        window._chat_container.refresh_mcp_tools()
    window._invoke_ui(_do)

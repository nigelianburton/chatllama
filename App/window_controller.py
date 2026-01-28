from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable, Optional

from Engine.logger import get_logger
from Engine.utilities import Utilities


class ExitIdleController:
    def __init__(
        self,
        log_file: Path,
        schedule_timer: Callable[[int, Callable[[], None]], None],
        quit_app: Callable[[], None],
        get_widget: Callable[[], object | None],
        get_cards: Callable[[], list[object]],
        logger=None,
    ) -> None:
        self._logger = logger or get_logger("ExitIdleController")
        self._log_file = log_file
        self._schedule_timer = schedule_timer
        self._quit_app = quit_app
        self._get_widget = get_widget
        self._get_cards = get_cards
        self._pending_description_thread: Optional[threading.Thread] = None

    def capture_screenshot(self):
        return Utilities.log_screenshot(
            self._log_file,
            widget=self._get_widget(),
            card_widgets=self._get_cards(),
        )

    def request_exit(self) -> None:
        self._logger.info("Exit-idle requested; capturing screenshot and starting description")
        _, description_thread = self.capture_screenshot()
        if description_thread is not None:
            self._logger.info("Screenshot description thread started; keeping window open until completion")
            self._pending_description_thread = description_thread
            self._schedule_timer(200, self._wait_for_description_and_exit)
            return
        self._quit_app()

    def _wait_for_description_and_exit(self) -> None:
        thread = self._pending_description_thread
        if thread is None:
            self._quit_app()
            return

        if thread.is_alive():
            self._schedule_timer(200, self._wait_for_description_and_exit)
            return

        self._logger.info("Screenshot description finished; exiting now")
        self._pending_description_thread = None
        self._quit_app()

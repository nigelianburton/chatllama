from __future__ import annotations

from typing import Callable

from Engine.logger import get_logger
from Engine.utilities import set_model_download_callback


class StatusMessageController:
    def __init__(
        self,
        get_text: Callable[[], str],
        set_text: Callable[[str], None],
        schedule_timer: Callable[[int, Callable[[], None]], None],
        logger=None,
    ) -> None:
        self._get_text = get_text
        self._set_text = set_text
        self._schedule_timer = schedule_timer
        self._logger = logger or get_logger("StatusMessageController")

    def show_message(self, message: str, duration_ms: int = 3000) -> None:
        self._logger.info("Status: %s", message)
        original_text = self._get_text()
        self._set_text(message)
        self._schedule_timer(duration_ms, lambda: self._set_text(original_text))


def attach_download_callback(
    controller: StatusMessageController,
    duration_ms: int = 5000,
) -> None:
    set_model_download_callback(lambda msg: controller.show_message(msg, duration_ms=duration_ms))

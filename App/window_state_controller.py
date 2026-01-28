from __future__ import annotations

from typing import Callable

from Engine.logger import get_logger
from App.ui_state import header_colors_for_state, model_title_text


class WindowStateController:
    def __init__(
        self,
        set_model_title: Callable[[str], None],
        set_progress_range: Callable[[int, int], None],
        set_progress_value: Callable[[int], None],
        set_header_color: Callable[[str, str], None],
        logger=None,
    ) -> None:
        self._set_model_title = set_model_title
        self._set_progress_range = set_progress_range
        self._set_progress_value = set_progress_value
        self._set_header_color = set_header_color
        self._logger = logger or get_logger("WindowStateController")

    def on_model_load_started(self) -> None:
        self._set_progress_range(0, 0)
        self._set_progress_value(0)

    def on_model_load_finished(self, success: bool) -> None:
        self._set_progress_range(0, 100)
        self._set_progress_value(0)

    def on_cache_warm_started(self) -> None:
        self._set_progress_range(0, 0)
        self._set_progress_value(0)

    def on_cache_warm_finished(self) -> None:
        self._set_progress_range(0, 100)
        self._set_progress_value(0)

    def on_model_changed(self, model_name: str) -> None:
        self._set_model_title(model_title_text(model_name))

    def on_model_state_updated(self, state: str) -> None:
        settings_color, chat_color = header_colors_for_state(state)
        self._set_header_color("Settings", settings_color)
        self._set_header_color("Chat", chat_color)

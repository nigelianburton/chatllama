from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable

from Engine.autorun import run_autorun


def start_autorun(
    layout,
    window,
    logger,
    autorun_args: list[str] | None,
    log_final_response: bool = False,
) -> None:
    if not autorun_args:
        return

    def _finish(success: bool, message: str) -> None:
        delay_ms = 1000
        if success:
            logger.info(
                "Autorun completion signaled; waiting %d ms then capturing screenshot and exiting",
                delay_ms,
            )
        else:
            logger.error("Autorun failed: %s", message)
        layout.invoke_ui(window, lambda: layout.schedule_exit(window, delay_ms))

    def _run() -> None:
        def _stage(text: str, image_paths: list[Path]) -> None:
            layout.autorun_stage_message(window, text, image_paths)

        def _submit() -> None:
            layout.autorun_submit_message(window)

        def _register_availability(callback: Callable[[str], None]) -> bool:
            return layout.register_availability_callback(window, callback)

        def _get_last_response() -> str:
            return layout.get_last_assistant_message(window)

        success, message = run_autorun(
            autorun_args,
            ui_stage_message=_stage,
            ui_submit_message=_submit,
            register_availability_callback=_register_availability,
            ui_get_last_response=_get_last_response,
        )
        if log_final_response:
            final_response = _get_last_response()
            logger.info("Autorun final response: %s", final_response)
        _finish(success, message)

    threading.Thread(target=_run, daemon=True).start()

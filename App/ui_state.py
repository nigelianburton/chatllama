from __future__ import annotations

from UI.ui_constants import HEADER_COLOR_FAULT, HEADER_COLOR_LOADING, HEADER_COLOR_READY


def header_colors_for_state(state: str) -> tuple[str, str]:
    if state == "Ready":
        return HEADER_COLOR_READY, HEADER_COLOR_READY
    if state == "Waiting":
        return HEADER_COLOR_READY, HEADER_COLOR_LOADING
    if state == "Loading":
        return HEADER_COLOR_LOADING, HEADER_COLOR_LOADING
    if state == "Fault":
        return HEADER_COLOR_FAULT, HEADER_COLOR_FAULT
    return HEADER_COLOR_FAULT, HEADER_COLOR_FAULT


def model_title_text(model_name: str) -> str:
    return f"Model: {model_name}" if model_name else "Model: None"

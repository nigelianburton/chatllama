from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Protocol

from Engine.logger import get_logger
from constants import (
    DEFAULT_MODEL_FILE,
    DEFAULT_TOOL_PREAMBLE_GENERAL,
    LLAMA_CPP_MODEL_INIT_FILE,
    PEPPER_SETTINGS_FILE,
    SETTINGS_DEV,
    SETTINGS_HOME,
    SETTINGS_WORK,
)


class ModelInfoLike(Protocol):
    name: str
    folder: str


_logger = get_logger("LlamaCppServer")
_settings_data: dict | None = None
_settings_path: Path | None = None
_models_preset_path: Path | None = None


def load_settings() -> dict:
    global _settings_data, _settings_path
    if _settings_data is not None and _settings_path is not None:
        return _settings_data

    candidates = [
        Path(SETTINGS_DEV) / PEPPER_SETTINGS_FILE,
        Path(SETTINGS_WORK) / PEPPER_SETTINGS_FILE,
        Path(SETTINGS_HOME) / PEPPER_SETTINGS_FILE,
    ]
    for path in candidates:
        if path.exists():
            _settings_path = path
            break
    if _settings_path is None:
        _settings_path = candidates[0]
        _settings_path.parent.mkdir(parents=True, exist_ok=True)
        _settings_data = {
            "settings_folder": str(_settings_path.parent),
            "default_model": DEFAULT_MODEL_FILE,
            "model_cache": {},
        }
        save_settings(_settings_data)
        return _settings_data

    try:
        _settings_data = json.loads(_settings_path.read_text())
    except Exception:
        _settings_data = {}

    _settings_data.setdefault("settings_folder", str(_settings_path.parent))
    _settings_data.setdefault("default_model", DEFAULT_MODEL_FILE)
    if not _settings_data.get("tool_preamble_general"):
        _settings_data["tool_preamble_general"] = DEFAULT_TOOL_PREAMBLE_GENERAL
        save_settings(_settings_data)
    if "tool_preamble_cards" in _settings_data:
        _settings_data.pop("tool_preamble_cards", None)
        save_settings(_settings_data)
    _settings_data.setdefault("model_cache", {})
    return _settings_data


def load_settings_fresh() -> dict:
    global _settings_data, _settings_path
    _settings_data = None
    _settings_path = None
    return load_settings()


def save_settings(settings: dict) -> None:
    if _settings_path is None:
        return
    try:
        _settings_path.write_text(json.dumps(settings, indent=2))
    except Exception as exc:
        _logger.warning("Failed to write settings cache: %s", exc)


def update_default_model(model_name: str) -> None:
    if not model_name:
        return
    settings = load_settings()
    settings["default_model"] = model_name
    save_settings(settings)


def get_models_preset_path() -> Path:
    global _models_preset_path
    if _models_preset_path is not None:
        return _models_preset_path
    settings = load_settings()
    settings_folder = Path(settings.get("settings_folder", SETTINGS_DEV))
    _models_preset_path = settings_folder / LLAMA_CPP_MODEL_INIT_FILE
    return _models_preset_path


def write_models_preset(preset_path: Path, models: list[ModelInfoLike]) -> None:
    try:
        lines: list[str] = ["version = 1", "", "[*]", "", ""]
        seen: set[str] = set()
        for model in models:
            name = model.name
            if not name:
                continue
            section = name
            if section in seen:
                continue
            seen.add(section)
            model_path = Path(model.folder) / f"{name}.gguf"
            if not model_path.exists():
                model_path = Path(model.folder) / name
            lines.append(f"[{section}]")
            lines.append(f"model = {model_path}")
            mmproj_path = find_mmproj_path(Path(model.folder), name)
            if mmproj_path:
                lines.append(f"mmproj = {mmproj_path}")
            lines.append("")
        preset_path.parent.mkdir(parents=True, exist_ok=True)
        preset_path.write_text("\n".join(lines))
        _logger.info("Wrote models preset: %s", preset_path)
    except Exception as exc:
        _logger.warning("Failed to write models preset: %s", exc)


def find_mmproj_path(folder: Path, model_name: str) -> Optional[Path]:
    if not folder.exists():
        return None
    candidates = sorted(folder.glob("*.mmproj*.gguf"))
    if not candidates:
        return None
    lowered = model_name.lower()
    for candidate in candidates:
        if lowered in candidate.name.lower():
            return candidate
    return candidates[0]

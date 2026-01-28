from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from constants import DEFAULT_MODEL_FILE, DEFAULT_TOOL_PREAMBLE_GENERAL, PEPPER_SETTINGS_FILE


class SettingsStore:
    def __init__(self, settings_folder: Path) -> None:
        self._settings_folder = settings_folder

    @property
    def settings_path(self) -> Path:
        return self._settings_folder / PEPPER_SETTINGS_FILE

    def ensure_settings_file(self) -> None:
        self._settings_folder.mkdir(parents=True, exist_ok=True)
        settings_path = self.settings_path
        if not settings_path.exists():
            settings_path.write_text(
                json.dumps(
                    {
                        "settings_folder": str(self._settings_folder),
                        "default_model": DEFAULT_MODEL_FILE,
                        "tool_preamble_general": DEFAULT_TOOL_PREAMBLE_GENERAL,
                        "built_in_mcps": {},
                    },
                    indent=2,
                )
            )
            return

        data = self._load_settings_data()
        dirty = False
        if "default_model" not in data:
            data["default_model"] = DEFAULT_MODEL_FILE
            dirty = True
        if not data.get("tool_preamble_general"):
            data["tool_preamble_general"] = DEFAULT_TOOL_PREAMBLE_GENERAL
            dirty = True
        if "tool_preamble_cards" in data:
            data.pop("tool_preamble_cards", None)
            dirty = True
        if "built_in_mcps" not in data:
            data["built_in_mcps"] = {}
            dirty = True
        if dirty:
            self._save_settings_data(data)

    def _load_settings_data(self) -> dict[str, Any]:
        settings_path = self.settings_path
        if not settings_path.exists():
            return {}
        try:
            return json.loads(settings_path.read_text())
        except Exception:
            return {}

    def _save_settings_data(self, data: dict[str, Any]) -> None:
        self.settings_path.write_text(json.dumps(data, indent=2))

    def load_settings_cache(self) -> dict[str, Any]:
        return self._load_settings_data()

    def get_mcp_settings(self) -> dict[str, Any]:
        data = self._load_settings_data()
        return data.get("mcp_settings", {})

    def save_mcp_settings(self, mcp_data: dict[str, Any]) -> None:
        data = self._load_settings_data()
        data["mcp_settings"] = mcp_data
        self._save_settings_data(data)

    def get_mcp_state(self, name: str) -> dict[str, Any]:
        data = self._load_settings_data()
        mcp_settings = data.setdefault("mcp_settings", {})
        servers = mcp_settings.setdefault("servers", {})
        return servers.setdefault(name, {})

    def store_mcp_state(self, name: str, state: dict[str, Any], mcp_folder: Path | None = None) -> None:
        data = self._load_settings_data()
        mcp_settings = data.setdefault("mcp_settings", {})
        servers = mcp_settings.setdefault("servers", {})
        servers[name] = state
        if mcp_folder is not None:
            mcp_settings["folder"] = str(mcp_folder)
        data["mcp_settings"] = mcp_settings
        self._save_settings_data(data)

    def get_built_in_mcp_state(self, name: str) -> dict[str, Any]:
        data = self._load_settings_data()
        built_in = data.setdefault("built_in_mcps", {})
        return built_in.setdefault(name, {})

    def store_built_in_mcp_state(self, name: str, state: dict[str, Any]) -> None:
        data = self._load_settings_data()
        built_in = data.setdefault("built_in_mcps", {})
        built_in[name] = state
        data["built_in_mcps"] = built_in
        self._save_settings_data(data)

    def load_tool_preamble_general(self) -> str:
        data = self._load_settings_data()
        general = data.get("tool_preamble_general") or ""
        return general or DEFAULT_TOOL_PREAMBLE_GENERAL

    def save_tool_preamble_general(self, text: str) -> None:
        data = self._load_settings_data()
        data["tool_preamble_general"] = text or DEFAULT_TOOL_PREAMBLE_GENERAL
        data.pop("tool_preamble_cards", None)
        self._save_settings_data(data)

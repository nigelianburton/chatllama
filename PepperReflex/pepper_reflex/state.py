from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
from datetime import datetime
import urllib.error
import urllib.request
from typing import Dict, List, TypedDict

import reflex as rx

from constants import PEPPER_SETTINGS_FILE, SETTINGS_DEV, SETTINGS_HOME, SETTINGS_WORK

_control_process: subprocess.Popen | None = None

SETTINGS_BG = "#f7e0e0"
CHAT_BG = "#e0f7e0"
CARDS_BG = "#e0e8f7"
TOGGLE_ON_COLOR = "#cfe8ff"
TOGGLE_OFF_COLOR = "#f0f0f0"
HEADER_COLOR_READY = "#b6e3b6"
HEADER_COLOR_LOADING = "#d9d9d9"
HEADER_COLOR_FAULT = "#f5b7b1"


class BaseState(rx.State):
    show_settings: bool = True
    show_chat: bool = True
    show_cards: bool = True

    model_name: str = "None"
    model_state: str = "Ready"
    progress: int = 50
    status_text: str = ""
    model_options: List[str] = ["Loading..."]
    selected_model: str = "Loading..."
    polling_active: bool = True
    last_poll_ts: str = ""
    autorun_status: str = "Idle"
    control_service_status: str = "Unknown"

    layout_preset: str = "Equal"
    settings_ratio: float = 1.0
    chat_ratio: float = 1.0
    cards_ratio: float = 1.0

    def toggle_settings(self) -> None:
        self.show_settings = not self.show_settings

    def toggle_chat(self) -> None:
        self.show_chat = not self.show_chat

    def toggle_cards(self) -> None:
        self.show_cards = not self.show_cards

    def set_layout_preset(self, preset: str) -> None:
        self.layout_preset = preset
        if preset == "Focus Settings":
            self.settings_ratio, self.chat_ratio, self.cards_ratio = 2.0, 1.0, 1.0
        elif preset == "Focus Chat":
            self.settings_ratio, self.chat_ratio, self.cards_ratio = 1.0, 2.0, 1.0
        elif preset == "Focus Cards":
            self.settings_ratio, self.chat_ratio, self.cards_ratio = 1.0, 1.0, 2.0
        else:
            self.settings_ratio, self.chat_ratio, self.cards_ratio = 1.0, 1.0, 1.0

    @staticmethod
    def _header_color(state: str) -> str:
        if state == "Ready":
            return HEADER_COLOR_READY
        if state in {"Waiting", "Loading"}:
            return HEADER_COLOR_LOADING
        if state == "Fault":
            return HEADER_COLOR_FAULT
        return HEADER_COLOR_FAULT

    @rx.var
    def settings_header_color(self) -> str:
        return self._header_color(self.model_state)

    @rx.var
    def chat_header_color(self) -> str:
        return self._header_color(self.model_state)

    @rx.var
    def cards_header_color(self) -> str:
        return CARDS_BG

    @rx.var
    def model_ready(self) -> bool:
        return self.model_state == "Ready"

    @rx.var
    def diagnostics_text(self) -> str:
        return (
            f"Control service: {self.control_service_status}\n"
            f"Control status: {self.model_state}\n"
            f"Active model: {self.model_name}\n"
            f"Last poll: {self.last_poll_ts or '-'}\n"
            f"Autorun: {self.autorun_status}"
        )

    @rx.var
    def settings_display(self) -> str:
        return "flex" if self.show_settings else "none"

    @rx.var
    def chat_display(self) -> str:
        return "flex" if self.show_chat else "none"

    @rx.var
    def cards_display(self) -> str:
        return "flex" if self.show_cards else "none"

    @rx.var
    def toggle_settings_color(self) -> str:
        return TOGGLE_ON_COLOR if self.show_settings else TOGGLE_OFF_COLOR

    @rx.var
    def toggle_chat_color(self) -> str:
        return TOGGLE_ON_COLOR if self.show_chat else TOGGLE_OFF_COLOR

    @rx.var
    def toggle_cards_color(self) -> str:
        return TOGGLE_ON_COLOR if self.show_cards else TOGGLE_OFF_COLOR

    @rx.var
    def grid_template_columns(self) -> str:
        settings = f"{self.settings_ratio}fr" if self.show_settings else "0fr"
        chat = f"{self.chat_ratio}fr" if self.show_chat else "0fr"
        cards = f"{self.cards_ratio}fr" if self.show_cards else "0fr"
        return f"{settings} {chat} {cards}"

    @rx.var
    def progress_value(self) -> int:
        return self.progress

    @rx.var
    def grid_template_columns(self) -> str:
        count = sum([self.show_settings, self.show_chat, self.show_cards])
        if count == 0:
            return "1fr"
        return " ".join(["1fr"] * count)

    def toggle_tool_enabled(self, name: str) -> None:
        items = getattr(self, "mcp_items", None)
        if not isinstance(items, list):
            return
        updated = []
        for item in items:
            if item.get("name") == name:
                updated.append({**item, "enabled": not bool(item.get("enabled"))})
            else:
                updated.append(item)
        self.mcp_items = updated

    def set_selected_model(self, value: str) -> None:
        self.selected_model = value

    def load_model(self) -> None:
        model_name = self.selected_model
        if not model_name or model_name in {"Loading...", "No models found"}:
            return
        return self.load_model_async(model_name)

    @staticmethod
    def _control_url(path: str) -> str:
        return f"http://127.0.0.1:8001{path}"

    @staticmethod
    def _fetch_json(url: str) -> dict:
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=2) as response:
            data = response.read().decode("utf-8")
        return json.loads(data) if data else {}

    @staticmethod
    def _post_json(url: str, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=5):
            return None

    @staticmethod
    def _control_service_running() -> bool:
        try:
            with socket.create_connection(("127.0.0.1", 8001), timeout=0.5):
                return True
        except OSError:
            return False

    @staticmethod
    def _start_control_service_process() -> None:
        global _control_process
        if _control_process is not None and _control_process.poll() is None:
            return
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        env = os.environ.copy()
        env["PYTHONPATH"] = repo_root
        _control_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "Engine.control_service",
            ],
            cwd=repo_root,
            env=env,
        )

    @staticmethod
    def _load_autorun_file(path: str) -> dict:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def _settings_paths() -> list[str]:
        return [
            os.path.join(SETTINGS_DEV, PEPPER_SETTINGS_FILE),
            os.path.join(SETTINGS_WORK, PEPPER_SETTINGS_FILE),
            os.path.join(SETTINGS_HOME, PEPPER_SETTINGS_FILE),
        ]

    @staticmethod
    def _settings_folder() -> str:
        for base in (SETTINGS_DEV, SETTINGS_WORK, SETTINGS_HOME):
            if os.path.isdir(base):
                return base
        return SETTINGS_DEV

    @classmethod
    def _load_settings_data(cls) -> dict:
        for path in cls._settings_paths():
            if os.path.isfile(path):
                try:
                    with open(path, "r", encoding="utf-8") as handle:
                        return json.load(handle)
                except Exception:
                    continue
        return {}

    @rx.event(background=True)
    async def poll_control_service(self) -> None:
        while True:
            if not self.polling_active:
                return
            status_data = None
            models_data = None
            try:
                status_data = await asyncio.to_thread(self._fetch_json, self._control_url("/status"))
                models_data = await asyncio.to_thread(self._fetch_json, self._control_url("/models"))
            except (urllib.error.URLError, json.JSONDecodeError):
                status_data = None
                models_data = None
            except Exception:
                status_data = None
                models_data = None

            async with self:
                self.last_poll_ts = datetime.now().isoformat(timespec="seconds")
                if isinstance(status_data, dict):
                    self.model_name = status_data.get("model_name") or "None"
                    self.model_state = status_data.get("status") or self.model_state
                if isinstance(models_data, dict):
                    models = models_data.get("models") or []
                    names = [m.get("name") for m in models if isinstance(m, dict) and m.get("name")]
                    if names:
                        self.model_options = names
                        if self.selected_model not in names:
                            self.selected_model = names[0]
                    else:
                        self.model_options = ["No models found"]
                        if self.selected_model != "No models found":
                            self.selected_model = "No models found"
            await asyncio.sleep(2)

    @rx.event(background=True)
    async def init_control_service(self) -> None:
        status_data = None
        models_data = None
        if not self._control_service_running():
            async with self:
                self.control_service_status = "Starting"
            await asyncio.to_thread(self._start_control_service_process)
            await asyncio.sleep(2)
        try:
            status_data = await asyncio.to_thread(self._fetch_json, self._control_url("/status"))
            models_data = await asyncio.to_thread(self._fetch_json, self._control_url("/models"))
        except (urllib.error.URLError, json.JSONDecodeError):
            status_data = None
            models_data = None
        except Exception:
            status_data = None
            models_data = None

        async with self:
            self.control_service_status = "Running" if self._control_service_running() else "Failed"
            if isinstance(status_data, dict):
                self.model_name = status_data.get("model_name") or "None"
                self.model_state = status_data.get("status") or self.model_state
            if isinstance(models_data, dict):
                models = models_data.get("models") or []
                names = [m.get("name") for m in models if isinstance(m, dict) and m.get("name")]
                if names:
                    self.model_options = names
                    if self.selected_model not in names:
                        self.selected_model = names[0]
                else:
                    self.model_options = ["No models found"]
                    if self.selected_model != "No models found":
                        self.selected_model = "No models found"
            if not self._control_service_running():
                self.model_options = ["Control service unavailable"]
                self.selected_model = "Control service unavailable"

        return [SettingsState.load_mcp_settings, ChatState.apply_autorun_from_query, BaseState.poll_control_service]

    @rx.event
    def on_before_unload(self) -> None:
        self.polling_active = False
        self.autorun_status = "Shutdown requested"


class BuiltInMcpItem(TypedDict):
    name: str
    enabled: bool
    methods: List[str]


class McpItem(TypedDict):
    name: str
    enabled: bool
    transport: str
    url: str
    port: str


class SettingsState(BaseState):
    mcp_items: List[McpItem] = [
        {
            "name": "internal",
            "enabled": True,
            "transport": "stdio",
            "url": "",
            "port": "",
        },
        {
            "name": "fashion_http",
            "enabled": False,
            "transport": "http",
            "url": "http://localhost",
            "port": "8014",
        },
    ]

    built_in_mcps: List[BuiltInMcpItem] = [
        {
            "name": "svg_card",
            "enabled": True,
            "methods": ["CreateCard", "DrawCard", "DeleteCard"],
        },
        {
            "name": "mcp_card_textviewer",
            "enabled": True,
            "methods": ["CreateCard", "DrawCard"],
        },
    ]

    @rx.event
    def load_mcp_settings(self) -> None:
        settings = self._load_settings_data()
        mcp_settings = settings.get("mcp_settings") if isinstance(settings, dict) else None
        servers = (mcp_settings or {}).get("servers") if isinstance(mcp_settings, dict) else None
        items: List[McpItem] = []
        if isinstance(servers, dict):
            for name, data in servers.items():
                if not isinstance(data, dict):
                    continue
                items.append(
                    {
                        "name": str(name),
                        "enabled": bool(data.get("enabled", False)),
                        "transport": str(data.get("transport", "stdio")),
                        "url": str(data.get("url", "")),
                        "port": str(data.get("port", "")),
                    }
                )
        if items:
            self.mcp_items = items

        built_in = settings.get("built_in_mcps") if isinstance(settings, dict) else None
        if isinstance(built_in, dict):
            updated: List[BuiltInMcpItem] = []
            for item in self.built_in_mcps:
                data = built_in.get(item["name"], {}) if isinstance(built_in, dict) else {}
                enabled = item["enabled"]
                if isinstance(data, dict) and "enabled" in data:
                    enabled = bool(data.get("enabled"))
                updated.append({**item, "enabled": enabled})
            self.built_in_mcps = updated

    @rx.event(background=True)
    async def load_model_async(self, model_name: str) -> None:
        try:
            await asyncio.to_thread(
                self._post_json,
                self._control_url("/load"),
                {"model_name": model_name},
            )
            async with self:
                self.model_state = "Loading"
        except Exception:
            async with self:
                self.model_state = "Fault"

    def delete_mcp(self) -> None:
        return None

    def toggle_mcp(self, name: str) -> None:
        updated = []
        for item in self.mcp_items:
            if item.get("name") == name:
                updated.append({**item, "enabled": not bool(item.get("enabled"))})
            else:
                updated.append(item)
        self.mcp_items = updated

    def toggle_built_in_mcp(self, name: str) -> None:
        updated = []
        for item in self.built_in_mcps:
            if item.get("name") == name:
                updated.append({**item, "enabled": not bool(item.get("enabled"))})
            else:
                updated.append(item)
        self.built_in_mcps = updated


class ChatState(BaseState):
    input_text: str = ""
    autorun_loaded: bool = False
    messages: List[Dict[str, str]] = [
        {"role": "assistant", "text": "Welcome to ChatLlama (Reflex UI demo)."},
        {"role": "user", "text": "Show me the model status and tools."},
        {"role": "assistant", "text": "Model: Ready. Tools: internal SVG cards enabled."},
    ]

    @staticmethod
    def _parse_autorun_payload(payload: dict) -> list[Dict[str, str]]:
        results: list[Dict[str, str]] = []
        messages = payload.get("messages", []) if isinstance(payload, dict) else []
        if not isinstance(messages, list):
            return results
        for entry in messages:
            if not isinstance(entry, dict):
                continue
            text = entry.get("text") or ""
            images = entry.get("images") or []
            if images:
                text = f"{text}\n[images: {', '.join(str(i) for i in images)}]".strip()
            if text:
                results.append({"role": "user", "text": str(text)})
        return results

    @rx.event
    def apply_autorun_from_query(self) -> None:
        params = self.router.url.query_parameters if self.router else {}
        autorun_path = params.get("autorun", "") if isinstance(params, dict) else ""
        if not autorun_path:
            return
        try:
            payload = self._load_autorun_file(autorun_path)
            items = self._parse_autorun_payload(payload)
        except Exception:
            self.autorun_status = "Autorun failed"
            return
        if not items:
            self.autorun_status = "Autorun empty"
            return
        self.messages = [*self.messages, *items]
        self.autorun_loaded = True
        self.autorun_status = "Autorun loaded"

    def set_input_text(self, value: str) -> None:
        self.input_text = value

    def send_message(self) -> None:
        text = self.input_text.strip()
        if not text:
            return
        self.messages.append({"role": "user", "text": text})
        self.messages.append({"role": "assistant", "text": "(demo reply)"})
        self.input_text = ""


class CardsState(BaseState):
    cards: List[str] = [
        "Card 01",
        "Card 02",
        "Card 03",
        "Card 04",
        "Card 05",
        "Card 06",
    ]

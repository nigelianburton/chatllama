from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from typing import Dict, List, TypedDict

import reflex as rx

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
    model_options: List[str] = []
    selected_model: str = ""

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
        if not model_name:
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

    @rx.event(background=True)
    async def poll_control_service(self) -> None:
        while True:
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
                if isinstance(status_data, dict):
                    self.model_name = status_data.get("model_name") or "None"
                    self.model_state = status_data.get("status") or self.model_state
                if isinstance(models_data, dict):
                    models = models_data.get("models") or []
                    names = [m.get("name") for m in models if isinstance(m, dict) and m.get("name")]
                    self.model_options = names
                    if names and self.selected_model not in names:
                        self.selected_model = names[0]
            await asyncio.sleep(2)


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
    model_ready: bool = True

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
    messages: List[Dict[str, str]] = [
        {"role": "assistant", "text": "Welcome to ChatLlama (Reflex UI demo)."},
        {"role": "user", "text": "Show me the model status and tools."},
        {"role": "assistant", "text": "Model: Ready. Tools: internal SVG cards enabled."},
    ]

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

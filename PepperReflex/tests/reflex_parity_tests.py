from __future__ import annotations

import json
import os
import sys
import unittest
import urllib.error
import urllib.request


CONTROL_BASE = "http://127.0.0.1:8001"


def _get_json(path: str) -> dict:
    request = urllib.request.Request(
        f"{CONTROL_BASE}{path}",
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=2) as response:
        data = response.read().decode("utf-8")
    return json.loads(data) if data else {}


class ReflexParityTests(unittest.TestCase):
    """Tests that validate Reflex parity steps once the app compiles."""

    def test_control_status_endpoint(self) -> None:
        try:
            payload = _get_json("/status")
        except urllib.error.URLError as exc:
            self.skipTest(f"control service unavailable: {exc}")
        self.assertIn("status", payload)
        self.assertIn("model_name", payload)

    def test_control_models_endpoint(self) -> None:
        try:
            payload = _get_json("/models")
        except urllib.error.URLError as exc:
            self.skipTest(f"control service unavailable: {exc}")
        self.assertIn("models", payload)
        self.assertIsInstance(payload["models"], list)

    def test_control_polling_ready(self) -> None:
        try:
            payload = _get_json("/status")
        except urllib.error.URLError as exc:
            self.skipTest(f"control service unavailable: {exc}")
        status = payload.get("status")
        self.assertIn(status, {"Ready", "Loading", "Fault", "Waiting"})

    def test_mcp_settings_loaded(self) -> None:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        from constants import PEPPER_SETTINGS_FILE, SETTINGS_DEV, SETTINGS_HOME, SETTINGS_WORK

        paths = [
            os.path.join(SETTINGS_DEV, PEPPER_SETTINGS_FILE),
            os.path.join(SETTINGS_WORK, PEPPER_SETTINGS_FILE),
            os.path.join(SETTINGS_HOME, PEPPER_SETTINGS_FILE),
        ]
        settings_path = next((p for p in paths if os.path.isfile(p)), None)
        if not settings_path:
            self.skipTest("PEPPER_SETTINGS.json not found")
        with open(settings_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        self.assertIn("mcp_settings", data)
        self.assertIn("built_in_mcps", data)

    def test_chat_cards_state_defaults(self) -> None:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        from pepper_reflex.state import CardsState, ChatState

        chat_field = ChatState.__fields__.get("messages")
        cards_field = CardsState.__fields__.get("cards")
        self.assertIsNotNone(chat_field)
        self.assertIsNotNone(cards_field)
        chat_default = chat_field.default_factory() if chat_field.default_factory else chat_field.default
        cards_default = cards_field.default_factory() if cards_field.default_factory else cards_field.default
        self.assertIsInstance(chat_default, list)
        self.assertIsInstance(cards_default, list)
        self.assertGreaterEqual(len(chat_default), 1)
        self.assertGreaterEqual(len(cards_default), 1)

    def test_autorun_payload_parsing(self) -> None:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        from pepper_reflex.state import ChatState

        autorun_path = os.path.join(repo_root, "autoruns", "autorun_capital.json")
        if not os.path.isfile(autorun_path):
            self.skipTest("autorun_capital.json not found")
        with open(autorun_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        items = ChatState._parse_autorun_payload(payload)
        self.assertIsInstance(items, list)
        self.assertGreaterEqual(len(items), 1)

    def test_diagnostics_fields(self) -> None:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        from pepper_reflex.state import BaseState

        self.assertIn("last_poll_ts", BaseState.__fields__)
        self.assertIn("polling_active", BaseState.__fields__)
        self.assertTrue(hasattr(BaseState, "on_before_unload"))


if __name__ == "__main__":
    unittest.main()

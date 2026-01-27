from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import shutil
import threading
import urllib.error
import urllib.request
import socket
import urllib.parse
from pathlib import Path

from PyQt6 import QtCore, QtWidgets

from Engine.logger import get_logger
from constants import (
    DEFAULT_MODEL_FILE,
    DEFAULT_TOOL_PREAMBLE_GENERAL,
    PEPPER_SETTINGS_FILE,
    INTERNAL_MCP_HOST,
    INTERNAL_MCP_PORT,
)
from UI.settings_local_models import SettingsLocalModels
from UI.settings_local_mcps import SettingsLocalMcps
from UI.settings_built_in_mcps import SettingsBuiltInMcps
from UI.settings_tools_preambles import SettingsToolsPreambles
from UI.setting_mcp_item import SettingsMcpItem


class ColumnSettingsWidget(QtWidgets.QWidget):
    model_load_started = QtCore.pyqtSignal()
    model_load_finished = QtCore.pyqtSignal(bool)
    cache_warm_started = QtCore.pyqtSignal()
    cache_warm_finished = QtCore.pyqtSignal()
    model_changed = QtCore.pyqtSignal(str)
    model_state_updated = QtCore.pyqtSignal(str)
    mcp_settings_changed = QtCore.pyqtSignal()

    def __init__(self, settings_folder: Path) -> None:
        super().__init__()
        self._logger = get_logger(self)
        self._settings_folder = settings_folder
        self._model_items: list[tuple[str, str]] = []
        self._llama_module = None
        self._load_thread: QtCore.QThread | None = None
        self._load_worker: QtCore.QObject | None = None
        self._last_model_state: tuple[str, str] | None = None
        self._last_load_enabled: bool | None = None
        self._mcp_folder = Path(__file__).resolve().parents[1] / "MCP_Local"
        self._mcp_entries: dict[str, SettingsMcpItem] = {}
        self._built_in_entries: dict[str, SettingsMcpItem] = {}
        self._mcp_polling = False
        self._mcp_poll_lock = threading.Lock()
        self._mcp_timer = QtCore.QTimer(self)
        self._mcp_timer.setInterval(5000)
        self._mcp_timer.timeout.connect(self._poll_http_endpoints)
        self._mcp_timer.start()
        self._load_settings_cache()
        self._ensure_settings_file()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self._model_selector = SettingsLocalModels()
        layout.addWidget(self._model_selector)

        self._model_status = self._model_selector.status_label
        self._model_combo = self._model_selector.model_combo
        self._load_button = self._model_selector.load_button

        self._model_combo.currentIndexChanged.connect(self._refresh_load_button)
        self._load_button.clicked.connect(self._on_load_clicked)

        self._mcp_widget = SettingsLocalMcps()
        layout.addWidget(self._mcp_widget)

        self._mcp_folder_edit = self._mcp_widget.folder_edit
        self._mcp_folder_edit.setText(str(self._mcp_folder))
        self._mcp_folder_button = self._mcp_widget.folder_button
        self._mcp_add_button = self._mcp_widget.add_local_button
        self._mcp_add_file_edit = self._mcp_widget.add_file_edit
        self._mcp_add_file_button = self._mcp_widget.add_file_button
        self._mcp_panel = self._mcp_widget.panel
        self._mcp_panel_container = self._mcp_widget.panel_container
        self._mcp_panel_layout = self._mcp_widget.panel_layout

        self._mcp_folder_button.clicked.connect(self._browse_mcp_folder)
        self._mcp_add_file_button.clicked.connect(self._browse_mcp_file)
        self._mcp_add_button.clicked.connect(self._add_local_mcp)

        self._built_in_widget = SettingsBuiltInMcps()
        layout.addWidget(self._built_in_widget)

        self._tool_preamble_widget = SettingsToolsPreambles()
        layout.addWidget(self._tool_preamble_widget)

        self._tool_preamble_general_edit = self._tool_preamble_widget.general_item.text_edit
        self._tool_preamble_general_edit.setPlaceholderText(DEFAULT_TOOL_PREAMBLE_GENERAL)
        self._tool_preamble_general_save = self._tool_preamble_widget.general_item.save_button
        self._tool_preamble_general_save.clicked.connect(self._save_tool_preamble)


        placeholder = QtWidgets.QLabel("Settings")
        placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("background-color: rgba(255, 255, 255, 0.4); border: 1px dashed #999;")
        layout.addWidget(placeholder, 1)

        self._register_model_discovery()
        self._refresh_mcp_list()
        self._refresh_built_in_mcps()
        self._load_tool_preamble()

    def _ensure_settings_file(self) -> None:
        self._settings_folder.mkdir(parents=True, exist_ok=True)
        settings_path = self._settings_folder / PEPPER_SETTINGS_FILE
        if not settings_path.exists():
            settings_path.write_text(
                json.dumps(
                    {
                        "settings_folder": str(self._settings_folder),
                        "default_model": DEFAULT_MODEL_FILE,
                        "tool_preamble_general": DEFAULT_TOOL_PREAMBLE_GENERAL,
                    },
                    indent=2,
                )
            )
            return

        try:
            data = json.loads(settings_path.read_text())
        except Exception:
            data = {}

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
            settings_path.write_text(json.dumps(data, indent=2))

    def _load_settings_cache(self) -> None:
        settings_path = self._settings_folder / PEPPER_SETTINGS_FILE
        if not settings_path.exists():
            return
        try:
            data = json.loads(settings_path.read_text())
        except Exception:
            data = {}
        mcp_settings = data.get("mcp_settings", {})
        folder = mcp_settings.get("folder")
        if folder:
            self._mcp_folder = Path(folder)

    def _save_mcp_settings(self, mcp_data: dict) -> None:
        settings_path = self._settings_folder / PEPPER_SETTINGS_FILE
        try:
            data = json.loads(settings_path.read_text()) if settings_path.exists() else {}
        except Exception:
            data = {}
        data["mcp_settings"] = mcp_data
        settings_path.write_text(json.dumps(data, indent=2))

    def _get_built_in_mcp_state(self, name: str) -> dict:
        settings_path = self._settings_folder / PEPPER_SETTINGS_FILE
        try:
            data = json.loads(settings_path.read_text()) if settings_path.exists() else {}
        except Exception:
            data = {}
        built_in = data.setdefault("built_in_mcps", {})
        return built_in.setdefault(name, {})

    def _store_built_in_mcp_state(self, name: str, state: dict) -> None:
        settings_path = self._settings_folder / PEPPER_SETTINGS_FILE
        try:
            data = json.loads(settings_path.read_text()) if settings_path.exists() else {}
        except Exception:
            data = {}
        built_in = data.setdefault("built_in_mcps", {})
        built_in[name] = state
        settings_path.write_text(json.dumps(data, indent=2))
        self.mcp_settings_changed.emit()

    def _load_tool_preamble(self) -> None:
        settings_path = self._settings_folder / PEPPER_SETTINGS_FILE
        if not settings_path.exists():
            self._tool_preamble_general_edit.setPlainText(DEFAULT_TOOL_PREAMBLE_GENERAL)
            return
        try:
            data = json.loads(settings_path.read_text())
        except Exception:
            data = {}
        general = data.get("tool_preamble_general") or ""
        if not general:
            general = DEFAULT_TOOL_PREAMBLE_GENERAL
        self._tool_preamble_general_edit.setPlainText(general)
        if "tool_preamble_cards" in data:
            data.pop("tool_preamble_cards", None)
            settings_path.write_text(json.dumps(data, indent=2))

    def _save_tool_preamble(self) -> None:
        settings_path = self._settings_folder / PEPPER_SETTINGS_FILE
        try:
            data = json.loads(settings_path.read_text()) if settings_path.exists() else {}
        except Exception:
            data = {}
        general = self._tool_preamble_general_edit.toPlainText().strip()
        data["tool_preamble_general"] = general or DEFAULT_TOOL_PREAMBLE_GENERAL
        data.pop("tool_preamble_cards", None)
        settings_path.write_text(json.dumps(data, indent=2))


    def _browse_mcp_folder(self) -> None:
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select MCP Folder", str(self._mcp_folder))
        if not folder:
            return
        self._mcp_folder = Path(folder)
        self._mcp_folder_edit.setText(str(self._mcp_folder))
        self._refresh_mcp_list()

    def _browse_mcp_file(self) -> None:
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select MCP Python File",
            str(self._mcp_folder),
            "Python Files (*.py)",
        )
        if not file_path:
            return
        self._mcp_add_file_edit.setText(file_path)

    def _add_local_mcp(self) -> None:
        source_path = Path(self._mcp_add_file_edit.text()).expanduser()
        if not source_path.exists():
            return
        if source_path.suffix.lower() != ".py":
            return
        target_folder = Path(self._mcp_folder_edit.text()).expanduser()
        target_folder.mkdir(parents=True, exist_ok=True)
        target_path = target_folder / source_path.name
        try:
            shutil.copy2(source_path, target_path)
        except Exception as exc:
            self._logger.warning("Failed to add MCP file: %s", exc)
            return
        self._mcp_add_file_edit.clear()
        self._refresh_mcp_list()

    def _refresh_mcp_list(self) -> None:
        while self._mcp_panel_layout.count() > 1:
            item = self._mcp_panel_layout.takeAt(0)
            widget = item.widget() if item else None
            if widget:
                widget.deleteLater()

        self._mcp_entries.clear()
        mcp_folder = Path(self._mcp_folder_edit.text()).expanduser()
        if not mcp_folder.exists():
            return

        settings_path = self._settings_folder / PEPPER_SETTINGS_FILE
        try:
            data = json.loads(settings_path.read_text()) if settings_path.exists() else {}
        except Exception:
            data = {}
        mcp_settings = data.get("mcp_settings", {})
        servers = mcp_settings.get("servers", {})
        mcp_settings["folder"] = str(mcp_folder)

        for entry in sorted(mcp_folder.glob("*.py")):
            if entry.name.startswith("__"):
                continue
            name = entry.stem
            server_state = servers.get(name, {})
            widget = self._build_mcp_entry(name, entry, server_state)
            self._mcp_panel_layout.insertWidget(self._mcp_panel_layout.count() - 1, widget)

        self._save_mcp_settings({"folder": str(mcp_folder), "servers": servers})

    def _refresh_built_in_mcps(self) -> None:
        while self._built_in_widget.panel_layout.count() > 1:
            item = self._built_in_widget.panel_layout.takeAt(0)
            widget = item.widget() if item else None
            if widget:
                widget.deleteLater()

        self._built_in_entries.clear()

        internal_folder = Path(__file__).resolve().parents[1] / "MCP_Internal"
        if not internal_folder.exists():
            return

        self._built_in_widget.set_endpoint(INTERNAL_MCP_HOST, str(INTERNAL_MCP_PORT))

        for entry in sorted(internal_folder.glob("mcp_*.py")):
            name = entry.stem
            try:
                module = self._load_internal_module(name, entry)
            except Exception as exc:
                self._logger.warning("Failed to load built-in MCP %s: %s", name, exc)
                continue
            tool_names = self._get_internal_tool_names(module)
            preamble = self._get_internal_preamble(module, name)
            state = self._get_built_in_mcp_state(name)
            if preamble and not state.get("tool_preamble"):
                state["tool_preamble"] = preamble
                self._store_built_in_mcp_state(name, state)
            enabled = bool(state.get("enabled", True))

            def handle_toggle_change(checked: bool, mcp_name: str = name) -> None:
                state = self._get_built_in_mcp_state(mcp_name)
                state["enabled"] = checked
                if preamble and not state.get("tool_preamble"):
                    state["tool_preamble"] = preamble
                self._store_built_in_mcp_state(mcp_name, state)

            item = SettingsMcpItem(
                name=name,
                path=None,
                enabled=enabled,
                transport="http",
                url="",
                port="",
                on_delete=lambda: None,
                show_transport_controls=False,
                show_connection_fields=False,
                show_delete_button=False,
            )
            item.set_methods_badges(tool_names)
            item.set_preamble(state.get("tool_preamble") or preamble)
            item.toggle.toggled.connect(handle_toggle_change)

            self._built_in_entries[name] = item
            self._built_in_widget.panel_layout.insertWidget(
                self._built_in_widget.panel_layout.count() - 1,
                item,
            )

    def _load_internal_module(self, name: str, path: Path):
        spec = importlib.util.spec_from_file_location(f"MCP_Internal.{name}", path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Could not load internal MCP {name}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _get_internal_tool_names(self, module: object) -> list[str]:
        names = getattr(module, "MCP_TOOL_NAMES", None)
        if isinstance(names, list):
            return [str(name) for name in names]
        getter = getattr(module, "get_tool_names", None)
        if callable(getter):
            try:
                result = getter()
            except Exception:
                result = []
            if isinstance(result, list):
                return [str(name) for name in result]
        return []

    def _get_internal_preamble(self, module: object, name: str) -> str:
        getter = getattr(module, "get_instructions", None)
        if not callable(getter):
            return ""
        try:
            return str(getter(name) or "")
        except TypeError:
            return str(getter() or "")

    def _build_mcp_entry(self, name: str, path: Path, state: dict) -> QtWidgets.QWidget:
        enabled = bool(state.get("enabled", False))
        transport = state.get("transport", "stdio")
        item = SettingsMcpItem(
            name=name,
            path=path,
            enabled=enabled,
            transport=transport,
            url=state.get("url", "http://127.0.0.1"),
            port=str(state.get("port", "6820")),
            on_delete=lambda: self._delete_local_mcp(name, path),
        )

        def save_state() -> None:
            server_state = self._get_mcp_state(name)
            server_state["enabled"] = item.toggle.isChecked()
            server_state["transport"] = "http" if item.http_radio.isChecked() else "stdio"
            server_state["url"] = item.url_edit.text().strip()
            server_state["port"] = item.port_edit.text().strip()
            self._store_mcp_state(name, server_state)

        def handle_transport_change() -> None:
            item.update_http_visibility()
            server_state = self._get_mcp_state(name)
            server_state["discovered"] = False
            self._store_mcp_state(name, server_state)
            save_state()
            if item.toggle.isChecked():
                self._maybe_discover_methods(name)

        def handle_toggle_change() -> None:
            item.update_toggle_text(item.toggle.isChecked())
            save_state()
            self._set_method_widgets_enabled(name, item.toggle.isChecked())
            self._set_transport_widgets_enabled(name, item.toggle.isChecked())
            if item.toggle.isChecked():
                self._maybe_discover_methods(name)

        item.toggle.toggled.connect(handle_toggle_change)
        item.stdio_radio.toggled.connect(handle_transport_change)
        item.http_radio.toggled.connect(handle_transport_change)
        item.url_edit.textChanged.connect(save_state)
        item.port_edit.textChanged.connect(save_state)

        self._mcp_entries[name] = item

        self._populate_method_toggles(name, state)
        self._set_method_widgets_enabled(name, enabled)
        self._set_transport_widgets_enabled(name, enabled)
        return item

    def _delete_local_mcp(self, name: str, path: Path) -> None:
        try:
            if path.exists():
                path.unlink()
        except Exception as exc:
            self._logger.warning("Failed to delete MCP file: %s", exc)
        settings_path = self._settings_folder / PEPPER_SETTINGS_FILE
        try:
            data = json.loads(settings_path.read_text()) if settings_path.exists() else {}
        except Exception:
            data = {}
        mcp_settings = data.get("mcp_settings", {})
        servers = mcp_settings.get("servers", {})
        if name in servers:
            servers.pop(name, None)
            mcp_settings["servers"] = servers
            data["mcp_settings"] = mcp_settings
            settings_path.write_text(json.dumps(data, indent=2))
            self.mcp_settings_changed.emit()
        self._refresh_mcp_list()

    def _get_mcp_state(self, name: str) -> dict:
        settings_path = self._settings_folder / PEPPER_SETTINGS_FILE
        try:
            data = json.loads(settings_path.read_text()) if settings_path.exists() else {}
        except Exception:
            data = {}
        mcp_settings = data.setdefault("mcp_settings", {})
        servers = mcp_settings.setdefault("servers", {})
        return servers.setdefault(name, {})

    def _store_mcp_state(self, name: str, state: dict) -> None:
        settings_path = self._settings_folder / PEPPER_SETTINGS_FILE
        try:
            data = json.loads(settings_path.read_text()) if settings_path.exists() else {}
        except Exception:
            data = {}
        mcp_settings = data.setdefault("mcp_settings", {})
        servers = mcp_settings.setdefault("servers", {})
        servers[name] = state
        mcp_settings["folder"] = str(self._mcp_folder)
        self._save_mcp_settings(mcp_settings)
        self.mcp_settings_changed.emit()

    def _populate_method_toggles(self, name: str, state: dict) -> None:
        entry = self._mcp_entries.get(name)
        if not entry:
            return
        layout = entry.methods_layout
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget() if item else None
            if widget:
                widget.deleteLater()
        methods = state.get("methods", {})
        for method_name, enabled in methods.items():
            button = QtWidgets.QToolButton()
            button.setText(method_name)
            button.setCheckable(True)
            button.setChecked(bool(enabled))
            button.toggled.connect(lambda checked, mn=method_name: self._update_method_state(name, mn, checked))
            layout.addWidget(button)

    def _set_method_widgets_enabled(self, name: str, enabled: bool) -> None:
        entry = self._mcp_entries.get(name)
        if not entry:
            return
        layout = entry.methods_layout
        for index in range(layout.count()):
            widget = layout.itemAt(index).widget()
            if widget:
                widget.setEnabled(enabled)

    def _set_transport_widgets_enabled(self, name: str, enabled: bool) -> None:
        entry = self._mcp_entries.get(name)
        if not entry:
            return
        entry.stdio_radio.setEnabled(enabled)
        entry.http_radio.setEnabled(enabled)
        entry.url_label.setEnabled(enabled)
        entry.url_edit.setEnabled(enabled)
        entry.port_label.setEnabled(enabled)
        entry.port_edit.setEnabled(enabled)

    def _update_method_state(self, name: str, method_name: str, enabled: bool) -> None:
        state = self._get_mcp_state(name)
        methods = state.setdefault("methods", {})
        methods[method_name] = enabled
        self._store_mcp_state(name, state)

    def _maybe_discover_methods(self, name: str) -> None:
        entry = self._mcp_entries.get(name)
        if not entry:
            return
        state = self._get_mcp_state(name)
        if state.get("discovered", False):
            return
        transport = "http" if entry.http_radio.isChecked() else "stdio"
        if transport == "stdio":
            threading.Thread(target=self._discover_stdio_methods, args=(name,), daemon=True).start()
        else:
            threading.Thread(target=self._discover_http_methods, args=(name,), daemon=True).start()

    def _discover_stdio_methods(self, name: str) -> None:
        entry = self._mcp_entries.get(name)
        if not entry:
            return
        path = entry.path

        def _worker() -> None:
            from fastmcp import Client
            tools: list = []
            async def _run() -> None:
                async with Client(str(path)) as client:
                    items = await client.list_tools()
                    tools.extend(items)
            try:
                asyncio.run(_run())
            except Exception as exc:
                self._logger.warning("Failed to load stdio MCP methods: %s", exc)
                return
            QtCore.QMetaObject.invokeMethod(
                self,
                "_apply_methods_slot",
                QtCore.Qt.ConnectionType.QueuedConnection,
                QtCore.Q_ARG(str, name),
                QtCore.Q_ARG(object, tools),
            )

        threading.Thread(target=_worker, daemon=True).start()

    def _discover_http_methods(self, name: str) -> None:
        entry = self._mcp_entries.get(name)
        if not entry:
            return
        url = entry.url_edit.text().strip()
        port = entry.port_edit.text().strip()
        if not url:
            return
        server_url = f"{url}:{port}/mcp" if port else url

        def _worker() -> None:
            from fastmcp import Client
            tools: list = []
            async def _run() -> None:
                async with Client(server_url) as client:
                    items = await client.list_tools()
                    tools.extend(items)
            try:
                asyncio.run(_run())
            except Exception as exc:
                self._logger.warning("Failed to load http MCP methods: %s", exc)
                return
            QtCore.QMetaObject.invokeMethod(
                self,
                "_apply_methods_slot",
                QtCore.Qt.ConnectionType.QueuedConnection,
                QtCore.Q_ARG(str, name),
                QtCore.Q_ARG(object, tools),
            )

        threading.Thread(target=_worker, daemon=True).start()

    @QtCore.pyqtSlot(str, object)
    def _apply_methods_slot(self, name: str, tools: object) -> None:
        self._apply_methods(name, tools)

    def _apply_methods(self, name: str, tools: object) -> None:
        state = self._get_mcp_state(name)
        methods = state.setdefault("methods", {})
        for tool in tools or []:
            tool_name = getattr(tool, "name", None) or tool.get("name")
            if not tool_name:
                continue
            methods.setdefault(tool_name, True)
        state["discovered"] = True
        self._store_mcp_state(name, state)
        self._populate_method_toggles(name, state)
        self._set_method_widgets_enabled(name, state.get("enabled", False))

    def _poll_http_endpoints(self) -> None:
        with self._mcp_poll_lock:
            if self._mcp_polling:
                return
            self._mcp_polling = True

        targets: list[tuple[str, str, bool]] = []
        for name, entry in self._mcp_entries.items():
            if not entry.http_radio.isChecked():
                continue
            url = entry.url_edit.text().strip()
            port = entry.port_edit.text().strip()
            if not url:
                continue
            server_url = f"{url}:{port}/mcp" if port else url
            toggle_checked = bool(entry.toggle.isChecked())
            targets.append((name, server_url, toggle_checked))

        def _worker() -> None:
            results: list[tuple[str, bool, bool]] = []
            try:
                for name, server_url, toggle_checked in targets:
                    responsive = self._probe_http(server_url)
                    results.append((name, responsive, toggle_checked))
                try:
                    QtCore.QMetaObject.invokeMethod(
                        self,
                        "_apply_http_probe_results",
                        QtCore.Qt.ConnectionType.QueuedConnection,
                        QtCore.Q_ARG(object, results),
                    )
                except RuntimeError as exc:
                    # Widget likely destroyed during app shutdown; ignore to avoid crash.
                    self._logger.warning("HTTP probe results ignored during shutdown: %s", exc)
                    return
            finally:
                with self._mcp_poll_lock:
                    self._mcp_polling = False

        threading.Thread(target=_worker, daemon=True).start()

    @QtCore.pyqtSlot(object)
    def _apply_http_probe_results(self, results: object) -> None:
        for name, responsive, toggle_checked in results or []:
            entry = self._mcp_entries.get(name)
            if not entry:
                continue
            color = "#2e7d32" if responsive else "#b71c1c"
            entry.url_label.setStyleSheet(f"background-color: {color}; color: #fff; padding: 2px;")
            entry.port_label.setStyleSheet(f"background-color: {color}; color: #fff; padding: 2px;")
            if responsive and toggle_checked:
                self._maybe_discover_methods(name)

    def _probe_http(self, url: str) -> bool:
        try:
            parsed = urllib.parse.urlparse(url)
            host = parsed.hostname
            if not host:
                return False
            port = parsed.port
            if port is None:
                port = 443 if parsed.scheme == "https" else 80
            with socket.create_connection((host, port), timeout=1.5):
                return True
        except Exception:
            return False

    def _register_model_discovery(self) -> None:
        module_path = Path(__file__).parent.parent / "Engine" / "manager_models.py"
        spec = importlib.util.spec_from_file_location("manager_models", module_path)
        if spec is None or spec.loader is None:
            self._logger.error("Failed to load llamacpp-server module")
            return
        import sys
        module = sys.modules.get(spec.name)
        if module is None:
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)

        self._llama_module = module

        module.register_models_callback(self._on_models_discovered)
        module.register_model_state_callback(self._on_model_state)
        if hasattr(module, "register_cache_warm_callback"):
            module.register_cache_warm_callback(self._on_cache_warm_state)

    def _on_models_discovered(self, models: list, loaded_model: str | None) -> None:
        self._logger.info("Discovered %d models", len(models))
        if loaded_model:
            self._logger.info("Loaded model reported: %s", loaded_model)
        QtCore.QMetaObject.invokeMethod(
            self,
            "_populate_models_slot",
            QtCore.Qt.ConnectionType.QueuedConnection,
            QtCore.Q_ARG(object, models),
            QtCore.Q_ARG(object, loaded_model),
        )

    def _on_model_state(self, state: str, model_name: str | None) -> None:
        QtCore.QMetaObject.invokeMethod(
            self,
            "_update_model_status_slot",
            QtCore.Qt.ConnectionType.QueuedConnection,
            QtCore.Q_ARG(str, state),
            QtCore.Q_ARG(object, model_name),
        )

    def _on_cache_warm_state(self, state: str) -> None:
        QtCore.QMetaObject.invokeMethod(
            self,
            "_cache_warm_state_slot",
            QtCore.Qt.ConnectionType.QueuedConnection,
            QtCore.Q_ARG(str, state),
        )

    def _update_model_status(self, state: str, model_name: str | None) -> None:
        name = model_name or "None"
        new_state = (name, state)
        if new_state != self._last_model_state:
            self._logger.info("Model state update: %s (%s)", name, state)
            self._last_model_state = new_state
        self._model_status.setText(f"Model: {name} ({state})")
        self.model_changed.emit(name if name != "None" else "")
        self.model_state_updated.emit(state)

    @QtCore.pyqtSlot(object, object)
    def _populate_models_slot(self, models: list, loaded_model: str | None) -> None:
        self._populate_models(models, loaded_model)

    @QtCore.pyqtSlot(str, object)
    def _update_model_status_slot(self, state: str, model_name: str | None) -> None:
        self._update_model_status(state, model_name)

    @QtCore.pyqtSlot(str)
    def _cache_warm_state_slot(self, state: str) -> None:
        if state == "start":
            self.cache_warm_started.emit()
        elif state == "end":
            self.cache_warm_finished.emit()

    def _populate_models(self, models: list, loaded_model: str | None) -> None:
        self._logger.info("Populating models list: %d items", len(models))
        self._model_combo.clear()
        self._model_items = []
        self._model_combo.setEnabled(False)
        self._load_button.setEnabled(False)
        self._model_status.setText("Model: None")

        if not models:
            return

        for model in models:
            name = getattr(model, "name", None)
            folder = getattr(model, "folder", None)
            if not name:
                self._logger.info("Skipping model entry name=%s folder=%s", name, folder)
                continue
            self._model_combo.addItem(name, userData=folder or "")
            self._model_items.append((name, folder or ""))

        has_models = self._model_combo.count() > 0
        self._model_combo.setEnabled(has_models)
        self._load_button.setEnabled(has_models)
        self._logger.info("Model combo enabled=%s count=%d", has_models, self._model_combo.count())

        if not has_models:
            return

        if loaded_model and has_models:
            index = self._model_combo.findText(loaded_model)
            if index >= 0:
                self._model_combo.setCurrentIndex(index)
            else:
                stripped = Path(loaded_model).stem
                index = self._model_combo.findText(stripped)
                if index >= 0:
                    self._model_combo.setCurrentIndex(index)

        if not loaded_model:
            default_name = Path(DEFAULT_MODEL_FILE).stem
            index = self._model_combo.findText(default_name)
            if index >= 0:
                self._model_combo.setCurrentIndex(index)
        current_text = self._model_combo.currentText()
        if loaded_model:
            self._model_status.setText(f"Model: {Path(loaded_model).stem}")
        else:
            self._model_status.setText(f"Model: {current_text}")
        self._logger.info("Model selection set to: %s", current_text)
        self._logger.info("Load button enabled after model set: %s", self._load_button.isEnabled())
        self._refresh_load_button()

    def _refresh_load_button(self) -> None:
        has_models = self._model_combo.count() > 0
        self._load_button.setEnabled(has_models)
        if self._last_load_enabled != has_models:
            self._logger.info("Load button enabled=%s (count=%d)", has_models, self._model_combo.count())
            self._last_load_enabled = has_models

    def _on_load_clicked(self) -> None:
        self._logger.info("Load button clicked (enabled=%s)", self._load_button.isEnabled())
        if self._llama_module is None:
            self._logger.error("Llama server module not available")
            return
        folder = self._model_combo.currentData()
        name = self._model_combo.currentText()
        if not name:
            self._logger.error("No model selected")
            return
        model_path = None
        if folder:
            candidate = Path(folder) / f"{name}.gguf"
            model_path = str(candidate) if candidate.exists() else str(Path(folder) / name)
        model_ref = model_path or name
        self._start_model_load(model_ref)

    def _start_model_load(self, model_ref: str) -> None:
        if self._load_thread is not None:
            self._logger.info("Model load already in progress")
            return

        self.model_load_started.emit()

        class _Worker(QtCore.QObject):
            finished = QtCore.pyqtSignal(bool, object)

            def __init__(self, module, ref: str) -> None:
                super().__init__()
                self._module = module
                self._ref = ref

            @QtCore.pyqtSlot()
            def run(self) -> None:
                success = False
                error = None
                try:
                    self._module.load_model(self._ref)
                    success = True
                except Exception as exc:
                    error = exc
                self.finished.emit(success, error)

        thread = QtCore.QThread(self)
        worker = _Worker(self._llama_module, model_ref)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_load_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._load_thread = thread
        self._load_worker = worker
        thread.start()

    @QtCore.pyqtSlot(bool, object)
    def _on_load_finished(self, success: bool, error: object) -> None:
        if error is not None:
            self._logger.error("Model load failed: %s", error)
        self._load_thread = None
        self._load_worker = None
        self.model_load_finished.emit(success)

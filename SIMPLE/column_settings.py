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

from logger import get_logger
from constants import (
    DEFAULT_MODEL_FILE,
    MCP_LABEL_WIDTH,
    MCP_PORT_INPUT_WIDTH,
    PEPPER_SETTINGS_FILE,
    TOGGLE_DISABLED_COLOR,
    TOGGLE_OFF_COLOR,
    TOGGLE_ON_COLOR,
)
from settings_local_models import SettingsLocalModels
from settings_local_mcps import SettingsLocalMcps
from settings_built_in_mcps import SettingsBuiltInMcps, BuiltInMcpEntryWidget


class ColumnSettingsWidget(QtWidgets.QWidget):
    model_load_started = QtCore.pyqtSignal()
    model_load_finished = QtCore.pyqtSignal(bool)
    cache_warm_started = QtCore.pyqtSignal()
    cache_warm_finished = QtCore.pyqtSignal()
    model_changed = QtCore.pyqtSignal(str)
    model_state_updated = QtCore.pyqtSignal(str)

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
        self._mcp_folder = Path(__file__).parent / "test_mcp"
        self._mcp_entries: dict[str, dict[str, object]] = {}
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


        placeholder = QtWidgets.QLabel("Settings")
        placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("background-color: rgba(255, 255, 255, 0.4); border: 1px dashed #999;")
        layout.addWidget(placeholder, 1)

        self._register_model_discovery()
        self._refresh_mcp_list()
        self._refresh_built_in_mcps()

    def _ensure_settings_file(self) -> None:
        self._settings_folder.mkdir(parents=True, exist_ok=True)
        settings_path = self._settings_folder / PEPPER_SETTINGS_FILE
        if not settings_path.exists():
            settings_path.write_text(
                json.dumps(
                    {
                        "settings_folder": str(self._settings_folder),
                        "default_model": DEFAULT_MODEL_FILE,
                    },
                    indent=2,
                )
            )
            return

        try:
            data = json.loads(settings_path.read_text())
        except Exception:
            data = {}

        if "default_model" not in data:
            data["default_model"] = DEFAULT_MODEL_FILE
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

        cards_folder = Path(__file__).parent / "cards"
        if not cards_folder.exists():
            return

        local_ip = self._get_local_ip()

        for entry in sorted(cards_folder.glob("*.py")):
            if entry.name == "__init__.py":
                continue
            name = entry.stem
            widget = BuiltInMcpEntryWidget(
                name=name,
                url=f"http://{local_ip}",
                port="6821",
                methods=["CreateCard", "DrawCard", "DeleteCard"],
            )
            self._built_in_widget.panel_layout.insertWidget(
                self._built_in_widget.panel_layout.count() - 1,
                widget,
            )

    def _get_local_ip(self) -> str:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            sock.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def _build_mcp_entry(self, name: str, path: Path, state: dict) -> QtWidgets.QWidget:
        container = QtWidgets.QFrame()
        container.setStyleSheet("QFrame { border: 1px solid #ccc; background: #fafafa; }")
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        enabled = bool(state.get("enabled", False))
        transport = state.get("transport", "stdio")

        toggle_style = (
            f"QToolButton {{ background: {TOGGLE_OFF_COLOR}; padding: 4px 8px; border: 1px solid #999; color: #b00020; }}"
            f"QToolButton:checked {{ background: {TOGGLE_ON_COLOR}; color: #000000; }}"
            f"QToolButton:disabled {{ background: {TOGGLE_DISABLED_COLOR}; color: #777; }}"
        )

        toggle = QtWidgets.QToolButton()
        toggle.setCheckable(True)
        toggle.setChecked(enabled)
        toggle.setStyleSheet(toggle_style)

        def update_toggle_text(checked: bool) -> None:
            toggle.setText("✓" if checked else "✗")

        update_toggle_text(enabled)

        name_label = QtWidgets.QLabel(name)
        name_label.setStyleSheet("font-weight: bold;")

        stdio_radio = QtWidgets.QToolButton()
        stdio_radio.setText("stdio")
        stdio_radio.setCheckable(True)
        stdio_radio.setStyleSheet(toggle_style)

        http_radio = QtWidgets.QToolButton()
        http_radio.setText("http")
        http_radio.setCheckable(True)
        http_radio.setStyleSheet(toggle_style)

        transport_group = QtWidgets.QButtonGroup(container)
        transport_group.setExclusive(True)
        transport_group.addButton(stdio_radio)
        transport_group.addButton(http_radio)

        if transport == "http":
            http_radio.setChecked(True)
        else:
            stdio_radio.setChecked(True)

        delete_button = QtWidgets.QToolButton()
        delete_button.setText("✕")
        delete_button.setFixedWidth(22)
        delete_button.clicked.connect(lambda: self._delete_local_mcp(name, path))

        row.addWidget(toggle)
        row.addWidget(name_label, 1)
        row.addWidget(stdio_radio)
        row.addWidget(http_radio)
        row.addWidget(delete_button)
        layout.addLayout(row)

        http_row = QtWidgets.QHBoxLayout()
        http_row.setContentsMargins(0, 0, 0, 0)
        http_row.setSpacing(6)
        url_label = QtWidgets.QLabel("URL")
        port_label = QtWidgets.QLabel("PORT")
        url_edit = QtWidgets.QLineEdit(state.get("url", "http://127.0.0.1"))
        port_edit = QtWidgets.QLineEdit(str(state.get("port", "6820")))
        port_edit.setFixedWidth(MCP_PORT_INPUT_WIDTH)
        url_label.setMinimumWidth(MCP_LABEL_WIDTH)
        port_label.setMinimumWidth(MCP_LABEL_WIDTH)
        http_row.addWidget(url_label)
        http_row.addWidget(url_edit, 1)
        http_row.addWidget(port_label)
        http_row.addWidget(port_edit)
        layout.addLayout(http_row)

        methods_container = QtWidgets.QWidget()
        methods_layout = QtWidgets.QHBoxLayout(methods_container)
        methods_layout.setContentsMargins(0, 0, 0, 0)
        methods_layout.setSpacing(6)
        layout.addWidget(methods_container)

        http_row_widget = http_row

        def update_http_visibility() -> None:
            http_visible = http_radio.isChecked()
            url_label.setVisible(http_visible)
            url_edit.setVisible(http_visible)
            port_label.setVisible(http_visible)
            port_edit.setVisible(http_visible)

        update_http_visibility()

        def save_state() -> None:
            server_state = self._get_mcp_state(name)
            server_state["enabled"] = toggle.isChecked()
            server_state["transport"] = "http" if http_radio.isChecked() else "stdio"
            server_state["url"] = url_edit.text().strip()
            server_state["port"] = port_edit.text().strip()
            self._store_mcp_state(name, server_state)

        def handle_transport_change() -> None:
            update_http_visibility()
            server_state = self._get_mcp_state(name)
            server_state["discovered"] = False
            self._store_mcp_state(name, server_state)
            save_state()
            if toggle.isChecked():
                self._maybe_discover_methods(name)

        def handle_toggle_change() -> None:
            update_toggle_text(toggle.isChecked())
            save_state()
            self._set_method_widgets_enabled(name, toggle.isChecked())
            self._set_transport_widgets_enabled(name, toggle.isChecked())
            if toggle.isChecked():
                self._maybe_discover_methods(name)

        toggle.toggled.connect(handle_toggle_change)
        stdio_radio.toggled.connect(handle_transport_change)
        http_radio.toggled.connect(handle_transport_change)
        url_edit.textChanged.connect(save_state)
        port_edit.textChanged.connect(save_state)

        self._mcp_entries[name] = {
            "path": path,
            "toggle": toggle,
            "stdio_radio": stdio_radio,
            "http_radio": http_radio,
            "url_edit": url_edit,
            "port_edit": port_edit,
            "url_label": url_label,
            "port_label": port_label,
            "methods_layout": methods_layout,
            "delete_button": delete_button,
        }

        self._populate_method_toggles(name, state)
        self._set_method_widgets_enabled(name, enabled)
        self._set_transport_widgets_enabled(name, enabled)
        return container

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

    def _populate_method_toggles(self, name: str, state: dict) -> None:
        entry = self._mcp_entries.get(name)
        if not entry:
            return
        layout = entry["methods_layout"]
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
        layout = entry["methods_layout"]
        for index in range(layout.count()):
            widget = layout.itemAt(index).widget()
            if widget:
                widget.setEnabled(enabled)

    def _set_transport_widgets_enabled(self, name: str, enabled: bool) -> None:
        entry = self._mcp_entries.get(name)
        if not entry:
            return
        entry["stdio_radio"].setEnabled(enabled)
        entry["http_radio"].setEnabled(enabled)
        entry["url_label"].setEnabled(enabled)
        entry["url_edit"].setEnabled(enabled)
        entry["port_label"].setEnabled(enabled)
        entry["port_edit"].setEnabled(enabled)

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
        transport = "http" if entry["http_radio"].isChecked() else "stdio"
        if transport == "stdio":
            threading.Thread(target=self._discover_stdio_methods, args=(name,), daemon=True).start()
        else:
            threading.Thread(target=self._discover_http_methods, args=(name,), daemon=True).start()

    def _discover_stdio_methods(self, name: str) -> None:
        entry = self._mcp_entries.get(name)
        if not entry:
            return
        path = entry["path"]

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
        url = entry["url_edit"].text().strip()
        port = entry["port_edit"].text().strip()
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
        for name, entry in self._mcp_entries.items():
            if not entry["http_radio"].isChecked():
                continue
            url = entry["url_edit"].text().strip()
            port = entry["port_edit"].text().strip()
            if not url:
                continue
            server_url = f"{url}:{port}/mcp" if port else url
            responsive = self._probe_http(server_url)
            color = "#2e7d32" if responsive else "#b71c1c"
            entry["url_label"].setStyleSheet(f"background-color: {color}; color: #fff; padding: 2px;")
            entry["port_label"].setStyleSheet(f"background-color: {color}; color: #fff; padding: 2px;")
            if responsive and entry["toggle"].isChecked():
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
        module_path = Path(__file__).parent / "manager_models.py"
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

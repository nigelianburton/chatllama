from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable

from PyQt6 import QtCore, QtWidgets

from App.mcp_controller import MCPController
from App.settings_store import SettingsStore
from constants import INTERNAL_MCP_HOST, INTERNAL_MCP_PORT
from UI.setting_mcp_item import SettingsMcpItem
from UI.settings_built_in_mcps import SettingsBuiltInMcps
from UI.settings_local_mcps import SettingsLocalMcps


class MCPSettingsPanel(QtCore.QObject):
    def __init__(
        self,
        parent: QtWidgets.QWidget,
        widget: SettingsLocalMcps,
        built_in_widget: SettingsBuiltInMcps,
        settings_store: SettingsStore,
        mcp_controller: MCPController,
        logger,
        on_settings_changed: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        self._parent = parent
        self._widget = widget
        self._built_in_widget = built_in_widget
        self._settings_store = settings_store
        self._mcp_controller = mcp_controller
        self._logger = logger
        self._on_settings_changed = on_settings_changed

        self._mcp_folder = Path(__file__).resolve().parents[1] / "MCP_Local"
        self._mcp_entries: dict[str, SettingsMcpItem] = {}
        self._built_in_entries: dict[str, SettingsMcpItem] = {}
        self._mcp_polling = False
        self._mcp_poll_lock = threading.Lock()
        self._mcp_timer = QtCore.QTimer(self)
        self._mcp_timer.setInterval(5000)
        self._mcp_timer.timeout.connect(self._poll_http_endpoints)
        self._mcp_timer.start()

        self._mcp_folder_edit = self._widget.folder_edit
        self._mcp_folder_button = self._widget.folder_button
        self._mcp_add_button = self._widget.add_local_button
        self._mcp_add_file_edit = self._widget.add_file_edit
        self._mcp_add_file_button = self._widget.add_file_button
        self._mcp_panel_layout = self._widget.panel_layout

        self._mcp_folder_button.clicked.connect(self._browse_mcp_folder)
        self._mcp_add_file_button.clicked.connect(self._browse_mcp_file)
        self._mcp_add_button.clicked.connect(self._add_local_mcp)

        self._load_settings_cache()
        self._mcp_folder_edit.setText(str(self._mcp_folder))

    def refresh_all(self) -> None:
        self._refresh_mcp_list()
        self._refresh_built_in_mcps()

    def _load_settings_cache(self) -> None:
        data = self._settings_store.load_settings_cache()
        mcp_settings = data.get("mcp_settings", {})
        folder = mcp_settings.get("folder")
        if folder:
            self._mcp_folder = Path(folder)

    def _browse_mcp_folder(self) -> None:
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self._parent,
            "Select MCP Folder",
            str(self._mcp_folder),
        )
        if not folder:
            return
        self._mcp_folder = Path(folder)
        self._mcp_folder_edit.setText(str(self._mcp_folder))
        self._refresh_mcp_list()

    def _browse_mcp_file(self) -> None:
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self._parent,
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
        try:
            self._mcp_controller.copy_mcp_file(source_path, target_folder)
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

        mcp_settings = self._settings_store.get_mcp_settings()
        servers = mcp_settings.get("servers", {})
        mcp_settings["folder"] = str(mcp_folder)

        for entry in sorted(mcp_folder.glob("*.py")):
            if entry.name.startswith("__"):
                continue
            name = entry.stem
            server_state = servers.get(name, {})
            widget = self._build_mcp_entry(name, entry, server_state)
            self._mcp_panel_layout.insertWidget(self._mcp_panel_layout.count() - 1, widget)

        self._settings_store.save_mcp_settings({"folder": str(mcp_folder), "servers": servers})
        self._on_settings_changed()

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
                module = self._mcp_controller.load_internal_module(name, entry)
            except Exception as exc:
                self._logger.warning("Failed to load built-in MCP %s: %s", name, exc)
                continue
            tool_names = self._mcp_controller.get_internal_tool_names(module)
            preamble = self._mcp_controller.get_internal_preamble(module, name)
            state = self._settings_store.get_built_in_mcp_state(name)
            if preamble and not state.get("tool_preamble"):
                state["tool_preamble"] = preamble
                self._settings_store.store_built_in_mcp_state(name, state)
                self._on_settings_changed()
            enabled = bool(state.get("enabled", True))

            def handle_toggle_change(checked: bool, mcp_name: str = name) -> None:
                state = self._settings_store.get_built_in_mcp_state(mcp_name)
                state["enabled"] = checked
                if preamble and not state.get("tool_preamble"):
                    state["tool_preamble"] = preamble
                self._settings_store.store_built_in_mcp_state(mcp_name, state)
                self._on_settings_changed()

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
            server_state = self._settings_store.get_mcp_state(name)
            server_state["enabled"] = item.toggle.isChecked()
            server_state["transport"] = "http" if item.http_radio.isChecked() else "stdio"
            server_state["url"] = item.url_edit.text().strip()
            server_state["port"] = item.port_edit.text().strip()
            self._settings_store.store_mcp_state(name, server_state, self._mcp_folder)
            self._on_settings_changed()

        def handle_transport_change() -> None:
            item.update_http_visibility()
            server_state = self._settings_store.get_mcp_state(name)
            server_state["discovered"] = False
            self._settings_store.store_mcp_state(name, server_state, self._mcp_folder)
            self._on_settings_changed()
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
            self._mcp_controller.delete_mcp_file(path)
        except Exception as exc:
            self._logger.warning("Failed to delete MCP file: %s", exc)
        mcp_settings = self._settings_store.get_mcp_settings()
        servers = mcp_settings.get("servers", {})
        if name in servers:
            servers.pop(name, None)
            mcp_settings["servers"] = servers
            self._settings_store.save_mcp_settings(mcp_settings)
            self._on_settings_changed()
        self._refresh_mcp_list()

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
        state = self._settings_store.get_mcp_state(name)
        methods = state.setdefault("methods", {})
        methods[method_name] = enabled
        self._settings_store.store_mcp_state(name, state, self._mcp_folder)
        self._on_settings_changed()

    def _maybe_discover_methods(self, name: str) -> None:
        entry = self._mcp_entries.get(name)
        if not entry:
            return
        state = self._settings_store.get_mcp_state(name)
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
            try:
                tools = self._mcp_controller.discover_stdio_methods(path)
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
            try:
                tools = self._mcp_controller.discover_http_methods(server_url)
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
        state = self._settings_store.get_mcp_state(name)
        methods = state.setdefault("methods", {})
        for tool in tools or []:
            tool_name = getattr(tool, "name", None) or tool.get("name")
            if not tool_name:
                continue
            methods.setdefault(tool_name, True)
        state["discovered"] = True
        self._settings_store.store_mcp_state(name, state, self._mcp_folder)
        self._on_settings_changed()
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
                    responsive = self._mcp_controller.probe_http(server_url)
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

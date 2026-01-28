from __future__ import annotations

from pathlib import Path

from PyQt6 import QtCore, QtWidgets

from Engine.logger import add_log_listener, get_logger, remove_log_listener
from App.settings_store import SettingsStore
from App.model_controller import ModelController
from App.mcp_controller import MCPController
from constants import (
    DEFAULT_MODEL_FILE,
    DEFAULT_TOOL_PREAMBLE_GENERAL,
)
from UI.settings_local_models import SettingsLocalModels
from UI.settings_local_mcps import SettingsLocalMcps
from UI.settings_built_in_mcps import SettingsBuiltInMcps
from UI.settings_tools_preambles import SettingsToolsPreambles
from UI.setting_log import SettingLog
from UI.mcp_settings_panel import MCPSettingsPanel


class ColumnSettingsWidgets:
    def __init__(self, parent: QtWidgets.QWidget, mcp_folder: Path) -> None:
        self.layout = QtWidgets.QVBoxLayout(parent)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(8)

        self.model_selector = SettingsLocalModels()
        self.layout.addWidget(self.model_selector)

        self.model_status = self.model_selector.status_label
        self.model_combo = self.model_selector.model_combo
        self.load_button = self.model_selector.load_button

        self.mcp_widget = SettingsLocalMcps()
        self.layout.addWidget(self.mcp_widget)

        self.mcp_folder_edit = self.mcp_widget.folder_edit
        self.mcp_folder_edit.setText(str(mcp_folder))
        self.mcp_folder_button = self.mcp_widget.folder_button
        self.mcp_add_button = self.mcp_widget.add_local_button
        self.mcp_add_file_edit = self.mcp_widget.add_file_edit
        self.mcp_add_file_button = self.mcp_widget.add_file_button
        self.mcp_panel = self.mcp_widget.panel
        self.mcp_panel_container = self.mcp_widget.panel_container
        self.mcp_panel_layout = self.mcp_widget.panel_layout

        self.built_in_widget = SettingsBuiltInMcps()
        self.layout.addWidget(self.built_in_widget)

        self.tool_preamble_widget = SettingsToolsPreambles()
        self.layout.addWidget(self.tool_preamble_widget)

        self.tool_preamble_general_edit = self.tool_preamble_widget.general_item.text_edit
        self.tool_preamble_general_save = self.tool_preamble_widget.general_item.save_button

        self.setting_log = SettingLog()
        self.layout.addWidget(self.setting_log)

        self.placeholder = QtWidgets.QLabel("Settings")
        self.placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setStyleSheet("background-color: rgba(255, 255, 255, 0.4); border: 1px dashed #999;")
        self.layout.addWidget(self.placeholder, 1)




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
        self._model_controller = ModelController(self._logger)
        self._load_thread: QtCore.QThread | None = None
        self._load_worker: QtCore.QObject | None = None
        self._last_model_state: tuple[str, str] | None = None
        self._last_load_enabled: bool | None = None
        self._settings_store = SettingsStore(settings_folder)
        self._mcp_controller = MCPController(self._logger)
        self._settings_store.ensure_settings_file()

        self._widgets = ColumnSettingsWidgets(self, Path(__file__).resolve().parents[1] / "MCP_Local")
        self._model_selector = self._widgets.model_selector
        self._model_status = self._widgets.model_status
        self._model_combo = self._widgets.model_combo
        self._load_button = self._widgets.load_button
        self._setting_log = self._widgets.setting_log
        self._log_handler = add_log_listener(self._setting_log.append_line)
        self.destroyed.connect(self._on_destroyed)

        self._model_combo.currentIndexChanged.connect(self._refresh_load_button)
        self._load_button.clicked.connect(self._on_load_clicked)

        self._mcp_panel = MCPSettingsPanel(
            self,
            self._widgets.mcp_widget,
            self._widgets.built_in_widget,
            self._settings_store,
            self._mcp_controller,
            self._logger,
            self.mcp_settings_changed.emit,
        )

        self._tool_preamble_widget = self._widgets.tool_preamble_widget
        self._tool_preamble_general_edit = self._widgets.tool_preamble_general_edit
        self._tool_preamble_general_edit.setPlaceholderText(DEFAULT_TOOL_PREAMBLE_GENERAL)
        self._tool_preamble_general_save = self._widgets.tool_preamble_general_save
        self._tool_preamble_general_save.clicked.connect(self._save_tool_preamble)

        self._register_model_discovery()
        self._mcp_panel.refresh_all()
        self._load_tool_preamble()

    def _on_destroyed(self, *_: object) -> None:
        if self._log_handler is not None:
            remove_log_listener(self._log_handler)
            self._log_handler = None

    def _load_tool_preamble(self) -> None:
        general = self._settings_store.load_tool_preamble_general()
        self._tool_preamble_general_edit.setPlainText(general)

    def _save_tool_preamble(self) -> None:
        general = self._tool_preamble_general_edit.toPlainText().strip()
        self._settings_store.save_tool_preamble_general(general)

    def _register_model_discovery(self) -> None:
        registered = self._model_controller.register_callbacks(
            self._on_models_discovered,
            self._on_model_state,
            self._on_cache_warm_state,
        )
        if not registered:
            self._logger.error("Model controller unavailable")

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
        if self._model_controller is None:
            self._logger.error("Model controller not available")
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
        worker = _Worker(self._model_controller, model_ref)
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

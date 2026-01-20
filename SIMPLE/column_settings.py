from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from PyQt6 import QtCore, QtWidgets

from logger import get_logger
from constants import DEFAULT_MODEL_FILE


class ColumnSettingsWidget(QtWidgets.QWidget):
    def __init__(self, settings_folder: Path) -> None:
        super().__init__()
        self._logger = get_logger(self)
        self._settings_folder = settings_folder
        self._model_items: list[tuple[str, str]] = []
        self._llama_module = None
        self._ensure_settings_file()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self._model_status = QtWidgets.QLabel("Model: None")
        self._model_status.setStyleSheet("color: #1c7c1c; font-weight: bold;")
        layout.addWidget(self._model_status)

        top_row = QtWidgets.QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        self._model_combo = QtWidgets.QComboBox()
        self._model_combo.setEnabled(False)
        self._model_combo.currentIndexChanged.connect(self._refresh_load_button)

        self._load_button = QtWidgets.QPushButton("Load")
        self._load_button.setEnabled(False)
        self._load_button.clicked.connect(self._on_load_clicked)

        top_row.addWidget(self._model_combo, 1)
        top_row.addWidget(self._load_button)
        layout.addLayout(top_row)

        placeholder = QtWidgets.QLabel("Settings")
        placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("background-color: rgba(255, 255, 255, 0.4); border: 1px dashed #999;")
        layout.addWidget(placeholder, 1)

        self._register_model_discovery()

    def _ensure_settings_file(self) -> None:
        self._settings_folder.mkdir(parents=True, exist_ok=True)
        settings_path = self._settings_folder / "simple_llama_settings.json"
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

    def _register_model_discovery(self) -> None:
        module_path = Path(__file__).parent / "llamacpp-server.py"
        spec = importlib.util.spec_from_file_location("llamacpp_server", module_path)
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

    def _update_model_status(self, state: str, model_name: str | None) -> None:
        name = model_name or "None"
        self._logger.info("Model state update: %s (%s)", name, state)
        self._model_status.setText(f"Model: {name} ({state})")

    @QtCore.pyqtSlot(object, object)
    def _populate_models_slot(self, models: list, loaded_model: str | None) -> None:
        self._populate_models(models, loaded_model)

    @QtCore.pyqtSlot(str, object)
    def _update_model_status_slot(self, state: str, model_name: str | None) -> None:
        self._update_model_status(state, model_name)

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
            if not name or not folder:
                self._logger.info("Skipping model entry name=%s folder=%s", name, folder)
                continue
            self._model_combo.addItem(name, userData=folder)
            self._model_items.append((name, folder))

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
        self._logger.info("Load button enabled=%s (count=%d)", has_models, self._model_combo.count())

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
        try:
            self._llama_module.load_model(model_ref)
        except Exception as exc:
            self._logger.error("Model load failed: %s", exc)

import logging
from typing import Optional, Iterable, Tuple
from PyQt6 import QtCore, QtWidgets

logger = logging.getLogger(__name__)


class _SpinAdapter:
    """Adapter to mimic QSpinBox API over a QLineEdit for compatibility."""
    def __init__(self, edit: QtWidgets.QLineEdit, default: int = 16384) -> None:
        self._edit = edit
        self._default = default

    def value(self) -> int:
        try:
            return int(self._edit.text().strip())
        except Exception:
            return self._default

    def setValue(self, v: int) -> None:
        self._edit.setText(str(v))


class LlmSettingsPanel(QtWidgets.QFrame):
    """Reusable LLM settings panel with minimal rows.

    Rows:
    1) Header: "Local: <model name or None>"
    2) Model dropdown with Load button
    3) Context (text box, default 16384) and Temp (default 0.7)
    """

    model_load_requested = QtCore.pyqtSignal(str)
    model_selection_changed = QtCore.pyqtSignal(int)
    ctx_changed = QtCore.pyqtSignal(int)

    def __init__(self, *, title: str, default_ctx: int, show_maker: bool = False, show_current: bool = False, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName(f"LlmSettingsPanel_{title}")
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.setLineWidth(1)
        # Allow shrinking to any size when parent narrows
        self.setMinimumWidth(0)
        # Expand to fill parent width
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)

        self.title = title
        self.default_ctx = default_ctx
        self.show_maker = show_maker
        self.show_current = show_current

        self.model_combo: Optional[QtWidgets.QComboBox] = None
        self.model_load_btn: Optional[QtWidgets.QPushButton] = None
        self.model_status_label: Optional[QtWidgets.QLabel] = None
        self.ctx_edit: Optional[QtWidgets.QLineEdit] = None
        self.temp_edit: Optional[QtWidgets.QLineEdit] = None

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header: title + current model combined
        self.model_status_label = QtWidgets.QLabel()
        self.model_status_label.setWordWrap(True)
        layout.addWidget(self.model_status_label)
        # initialize with None in red
        self._update_model_status(None)

        self.model_combo = QtWidgets.QComboBox()
        self.model_combo.setStyleSheet("color: #f5f5f5;")
        self.model_combo.setMinimumWidth(0)  # Allow full shrinking
        self.model_combo.currentIndexChanged.connect(self.model_selection_changed.emit)
        logger.debug(f"[LlmSettingsPanel] model_combo created: sizeHint={self.model_combo.sizeHint()}, minimumWidth={self.model_combo.minimumWidth()}")

        self.model_load_btn = QtWidgets.QPushButton("Load")
        self.model_load_btn.setStyleSheet("color: #f5f5f5;")
        self.model_load_btn.setFixedWidth(48)
        self.model_load_btn.clicked.connect(self._on_load_clicked)
        model_row = QtWidgets.QHBoxLayout()
        model_row.setContentsMargins(0, 0, 0, 0)
        model_row.setSpacing(4)
        model_row.addWidget(self.model_combo, 1)
        model_row.addWidget(self.model_load_btn)
        model_row_widget = QtWidgets.QWidget()
        model_row_widget.setMinimumWidth(0)  # Allow full shrinking
        model_row_widget.setLayout(model_row)
        layout.addWidget(model_row_widget)
        logger.debug(f"[LlmSettingsPanel] model_row_widget created: sizeHint={model_row_widget.sizeHint()}, minimumWidth={model_row_widget.minimumWidth()}")

        if self.show_maker:
            self.maker_label = QtWidgets.QLabel("")
            self.maker_label.setStyleSheet("font-size: 9px; color: #f5f5f5; font-style: italic;")
            self.maker_label.setVisible(False)
            layout.addWidget(self.maker_label)

        params_row = QtWidgets.QHBoxLayout()
        params_row.setContentsMargins(0, 0, 0, 0)
        params_row.setSpacing(10)
        ctx_label = QtWidgets.QLabel("Context")
        ctx_label.setStyleSheet("color: #f5f5f5;")
        self.ctx_edit = QtWidgets.QLineEdit()
        self.ctx_edit.setText("16384")
        self.ctx_edit.setMinimumWidth(0)  # Allow full shrinking
        self.ctx_edit.setMaximumWidth(90)  # Prefer 90 but allow shrinking
        self.ctx_edit.editingFinished.connect(self._emit_ctx_changed)
        temp_label = QtWidgets.QLabel("Temp")
        temp_label.setStyleSheet("color: #f5f5f5;")
        self.temp_edit = QtWidgets.QLineEdit()
        self.temp_edit.setText("0.7")
        self.temp_edit.setMinimumWidth(0)  # Allow full shrinking
        self.temp_edit.setMaximumWidth(60)  # Prefer 60 but allow shrinking
        params_row.addWidget(ctx_label)
        params_row.addWidget(self.ctx_edit)
        params_row.addSpacing(8)
        params_row.addWidget(temp_label)
        params_row.addWidget(self.temp_edit)
        params_row.addStretch(1)
        params_row_widget = QtWidgets.QWidget()
        params_row_widget.setMinimumWidth(0)  # Allow full shrinking
        params_row_widget.setLayout(params_row)
        layout.addWidget(params_row_widget)
        # Provide compatibility adapter for existing code paths
        self.ctx_spin = _SpinAdapter(self.ctx_edit, default=16384)

        # No other rows per spec

        layout.addStretch(1)
        self.setLayout(layout)
        logger.debug(f"[LlmSettingsPanel] after setLayout: self.sizeHint={self.sizeHint()}, minimumWidth={self.minimumWidth()}, width={self.width()}")

        # Distinguish subpanel background from the parent Settings panel
        # Slightly different gray with subtle border and rounded corners
        self.setStyleSheet(
            """
            QFrame {
                background-color: #3a3f46;
                border: 1px solid #666666;
                border-radius: 6px;
            }
            """
        )
    def sizeHint(self) -> QtCore.QSize:
        # Remove any preferred width; keep the natural height so vertical layouts stay stable.
        base = super().sizeHint()
        return QtCore.QSize(0, base.height())

    def minimumSizeHint(self) -> QtCore.QSize:
        # Match the zero-width preference for layouts that consult minimums.
        base = super().minimumSizeHint()
        return QtCore.QSize(0, base.height())

    def populate_models(self, items: Iterable[Tuple[str, str]]) -> None:
        if not self.model_combo:
            return
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        for display, data in items:
            self.model_combo.addItem(display, userData=data)
        self.model_combo.blockSignals(False)

    def set_current_model(self, text: str) -> None:
        self._update_model_status(text)

    def set_status(self, text: str) -> None:
        # Status label removed; no-op to preserve compatibility
        return

    def set_maker(self, maker: str) -> None:
        # Maker label removed; no-op to preserve compatibility
        return

    def _on_load_clicked(self) -> None:
        if self.model_combo:
            model = self.model_combo.currentData() or self.model_combo.currentText()
            self.model_load_requested.emit(model)

    def _emit_ctx_changed(self) -> None:
        if not self.ctx_edit:
            return
        text = self.ctx_edit.text().strip()
        try:
            value = int(text)
        except Exception:
            value = 16384
            self.ctx_edit.setText(str(value))
        self.ctx_changed.emit(value)

    def _update_model_status(self, text: Optional[str]) -> None:
        if not self.model_status_label:
            return
        prefix = self.title
        if text and text.strip():
            self.model_status_label.setText(f"{prefix}: {text}")
            self.model_status_label.setStyleSheet("font-size: 12px; font-weight: 700; color: #f5f5f5;")
        else:
            self.model_status_label.setText(f"{prefix}: None")
            self.model_status_label.setStyleSheet("font-size: 12px; font-weight: 700; color: #ff4444;")

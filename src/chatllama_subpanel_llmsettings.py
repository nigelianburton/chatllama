import logging
from typing import Optional, Iterable, Tuple
from PyQt6 import QtCore, QtWidgets

logger = logging.getLogger(__name__)


class LlmSettingsPanel(QtWidgets.QFrame):
    """Reusable LLM settings panel (model + context + status)."""

    model_load_requested = QtCore.pyqtSignal(str)
    model_selection_changed = QtCore.pyqtSignal(int)
    ctx_changed = QtCore.pyqtSignal(int)

    def __init__(self, *, title: str, default_ctx: int, show_maker: bool = False, show_current: bool = False, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName(f"LlmSettingsPanel_{title}")
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.setLineWidth(1)

        self.title = title
        self.default_ctx = default_ctx
        self.show_maker = show_maker
        self.show_current = show_current

        self.model_combo: Optional[QtWidgets.QComboBox] = None
        self.model_load_btn: Optional[QtWidgets.QPushButton] = None
        self.maker_label: Optional[QtWidgets.QLabel] = None
        self.current_model_label: Optional[QtWidgets.QLabel] = None
        self.status_label: Optional[QtWidgets.QLabel] = None
        self.ctx_spin: Optional[QtWidgets.QSpinBox] = None

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Title label (simple text for now)
        title_label = QtWidgets.QLabel(self.title)
        title_label.setStyleSheet("font-size: 12px; font-weight: 700; color: #f5f5f5;")
        layout.addWidget(title_label)

        model_label = QtWidgets.QLabel("Model:")
        model_label.setStyleSheet("color: #f5f5f5;")
        self.model_combo = QtWidgets.QComboBox()
        self.model_combo.setStyleSheet("color: #f5f5f5;")
        self.model_combo.currentIndexChanged.connect(self.model_selection_changed.emit)

        self.model_load_btn = QtWidgets.QPushButton("Load Model")
        self.model_load_btn.setStyleSheet("color: #f5f5f5;")
        self.model_load_btn.clicked.connect(self._on_load_clicked)

        layout.addWidget(model_label)
        layout.addWidget(self.model_combo)
        layout.addWidget(self.model_load_btn)

        if self.show_maker:
            self.maker_label = QtWidgets.QLabel("")
            self.maker_label.setStyleSheet("font-size: 9px; color: #f5f5f5; font-style: italic;")
            self.maker_label.setVisible(False)
            layout.addWidget(self.maker_label)

        ctx_row = QtWidgets.QHBoxLayout()
        ctx_label = QtWidgets.QLabel("Context (tokens):")
        ctx_label.setStyleSheet("color: #f5f5f5;")
        self.ctx_spin = QtWidgets.QSpinBox()
        self.ctx_spin.setRange(512, 1048576)
        self.ctx_spin.setSingleStep(512)
        self.ctx_spin.setValue(self.default_ctx)
        self.ctx_spin.valueChanged.connect(self.ctx_changed.emit)
        ctx_row.addWidget(ctx_label)
        ctx_row.addWidget(self.ctx_spin, 1)
        ctx_row_widget = QtWidgets.QWidget()
        ctx_row_widget.setLayout(ctx_row)
        layout.addWidget(ctx_row_widget)

        if self.show_current:
            self.current_model_label = QtWidgets.QLabel("Model: None")
            self.current_model_label.setWordWrap(True)
            self.current_model_label.setStyleSheet("font-size: 10px; color: #f5f5f5; font-weight: bold;")
            layout.addWidget(self.current_model_label)

        self.status_label = QtWidgets.QLabel("Ready")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("font-size: 10px; color: #f5f5f5;")
        layout.addWidget(self.status_label)

        layout.addStretch(1)
        self.setLayout(layout)

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

    def populate_models(self, items: Iterable[Tuple[str, str]]) -> None:
        if not self.model_combo:
            return
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        for display, data in items:
            self.model_combo.addItem(display, userData=data)
        self.model_combo.blockSignals(False)

    def set_current_model(self, text: str) -> None:
        if self.current_model_label:
            self.current_model_label.setText(f"Model: {text}")

    def set_status(self, text: str) -> None:
        if self.status_label:
            self.status_label.setText(text)

    def set_maker(self, maker: str) -> None:
        if self.maker_label:
            self.maker_label.setText(maker)
            self.maker_label.setVisible(bool(maker))

    def _on_load_clicked(self) -> None:
        if self.model_combo:
            model = self.model_combo.currentData() or self.model_combo.currentText()
            self.model_load_requested.emit(model)

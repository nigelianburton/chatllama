import logging
from typing import Optional
from PyQt6 import QtCore, QtWidgets

logger = logging.getLogger(__name__)


class SettingsPanel(QtWidgets.QFrame):
    """Settings panel widget with model selection and configuration."""
    model_load_requested = QtCore.pyqtSignal(str)  # Emits model path
    model_selection_changed = QtCore.pyqtSignal(int)  # Emits index
    ctx_changed = QtCore.pyqtSignal(int)  # Emits context value
    mode_changed = QtCore.pyqtSignal(str)  # Emits "local" or "lm_studio"
    
    def __init__(self, default_ctx: int, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsPanel")
        self.setMinimumWidth(384)
        self.setMaximumWidth(384)
        self.setAutoFillBackground(True)
        
        # Make the panel visible as a rectangle with a border
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.setLineWidth(1)
        
        self.mode: str = "local"  # "local" or "lm_studio"
        self.default_ctx = default_ctx
        
        self.model_combo: Optional[QtWidgets.QComboBox] = None
        self.model_load_btn: Optional[QtWidgets.QPushButton] = None
        self.maker_label: Optional[QtWidgets.QLabel] = None
        self.current_model_label: Optional[QtWidgets.QLabel] = None
        self.status_label: Optional[QtWidgets.QLabel] = None
        self.ctx_spin: Optional[QtWidgets.QSpinBox] = None
        self.local_btn: Optional[QtWidgets.QPushButton] = None
        self.lm_studio_btn: Optional[QtWidgets.QPushButton] = None
        
        self._build_ui()
    
    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Mode toggle buttons at the top
        mode_row = QtWidgets.QHBoxLayout()
        self.local_btn = QtWidgets.QPushButton("Local")
        self.lm_studio_btn = QtWidgets.QPushButton("LM Studio")
        
        # Style the buttons
        self.local_btn.setCheckable(True)
        self.lm_studio_btn.setCheckable(True)
        self.local_btn.setChecked(True)
        self.lm_studio_btn.setChecked(False)
        
        self.local_btn.clicked.connect(lambda: self._set_mode("local"))
        self.lm_studio_btn.clicked.connect(lambda: self._set_mode("lm_studio"))
        
        mode_row.addWidget(self.local_btn)
        mode_row.addWidget(self.lm_studio_btn)
        layout.addLayout(mode_row)

        layout.addWidget(QtWidgets.QLabel("Settings"))

        # Model loading UI
        model_label = QtWidgets.QLabel("Model:")
        self.model_combo = QtWidgets.QComboBox()

        self.model_load_btn = QtWidgets.QPushButton("Load Model")
        self.model_load_btn.clicked.connect(self._on_load_clicked)
        self.model_combo.currentIndexChanged.connect(self._on_selection_changed)

        layout.addWidget(model_label)
        layout.addWidget(self.model_combo)
        
        # Maker label (shown only when model selected)
        self.maker_label = QtWidgets.QLabel("")
        self.maker_label.setStyleSheet("font-size: 9px; color: #888888; font-style: italic;")
        self.maker_label.setVisible(False)
        layout.addWidget(self.maker_label)
        
        layout.addWidget(self.model_load_btn)

        # Context tokens control
        ctx_row = QtWidgets.QHBoxLayout()
        ctx_label = QtWidgets.QLabel("Context (tokens):")
        self.ctx_spin = QtWidgets.QSpinBox()
        self.ctx_spin.setRange(512, 1048576)
        self.ctx_spin.setSingleStep(512)
        self.ctx_spin.setValue(self.default_ctx)
        self.ctx_spin.valueChanged.connect(self._on_ctx_changed)
        ctx_row.addWidget(ctx_label)
        ctx_row.addWidget(self.ctx_spin, 1)
        ctx_row_widget = QtWidgets.QWidget()
        ctx_row_widget.setLayout(ctx_row)
        layout.addWidget(ctx_row_widget)

        # Current model label
        self.current_model_label = QtWidgets.QLabel("Model: None")
        self.current_model_label.setWordWrap(True)
        self.current_model_label.setStyleSheet("font-size: 10px; color: #cccccc; font-weight: bold;")
        layout.addWidget(self.current_model_label)

        # Status label
        self.status_label = QtWidgets.QLabel("Ready")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("font-size: 10px; color: #aaaaaa;")
        layout.addWidget(self.status_label)

        layout.addStretch(1)
        self.setLayout(layout)
        
        # Initialize Local mode colors
        self._set_mode("local")
    
    def _set_mode(self, mode: str) -> None:
        """Set service mode and update panel background color."""
        self.mode = mode
        
        # Update button states
        self.local_btn.setChecked(mode == "local")
        self.lm_studio_btn.setChecked(mode == "lm_studio")
        
        # Change panel background using stylesheet
        if mode == "lm_studio":
            self.setStyleSheet("""
                #SettingsPanel {
                    background-color: #2a3f5f;
                    border: 1px solid #1a1a1a;
                    border-radius: 4px;
                }
            """)
            logger.info("Service mode: LM Studio")
        else:
            self.setStyleSheet("""
                #SettingsPanel {
                    background-color: #fffacd;
                    border: 1px solid #888888;
                    border-radius: 4px;
                }
            """)
            logger.info("Service mode: Local (llama-cpp-python)")
        
        self.mode_changed.emit(mode)
    
    def _on_load_clicked(self) -> None:
        """Emit signal when load button clicked."""
        if self.model_combo:
            model_path = self.model_combo.currentData() or self.model_combo.currentText()
            self.model_load_requested.emit(model_path)
    
    def _on_selection_changed(self, index: int) -> None:
        """Emit signal when model selection changes."""
        self.model_selection_changed.emit(index)
    
    def _on_ctx_changed(self, value: int) -> None:
        """Emit signal when context value changes."""
        self.ctx_changed.emit(value)

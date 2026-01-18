import logging
from typing import Optional
from PyQt6 import QtWidgets
from chatllama_subpanel_llmsettings import LlmSettingsPanel

logger = logging.getLogger(__name__)


class SettingsPanel(QtWidgets.QFrame):
    """Settings panel stacking local (cpp) and LM Studio controls."""
    
    def __init__(self, default_ctx: int, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsPanel")
        self.setMinimumWidth(0)
        self.setAutoFillBackground(True)
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.setLineWidth(1)
        policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Preferred)
        policy.setHorizontalStretch(1)
        self.setSizePolicy(policy)

        self.cpp_panel = LlmSettingsPanel(
            title="Local (llama.cpp)",
            default_ctx=default_ctx,
            show_maker=True,
            show_current=True,
        )
        self.lmstudio_panel = LlmSettingsPanel(
            title="LM Studio",
            default_ctx=default_ctx,
            show_maker=False,
            show_current=False,
        )

        self._build_ui()
    
    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        layout.addWidget(self.cpp_panel)
        layout.addWidget(self.lmstudio_panel)
        layout.addStretch(1)

        self.setStyleSheet(
            """
            #SettingsPanel {
                background-color: #30343a;
                border: 1px solid #888888;
                border-radius: 4px;
            }
            """
        )

        self.setLayout(layout)

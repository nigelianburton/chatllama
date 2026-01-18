import logging
from typing import Optional
from PyQt6 import QtWidgets, QtCore
from chatllama_subpanel_llmsettings import LlmSettingsPanel
from chatllama_subpanel_mcpinfo import McpInfoPanel

logger = logging.getLogger(__name__)


class SettingsPanel(QtWidgets.QFrame):
    """Settings panel stacking local (cpp), LM Studio, and MCP controls."""
    
    def __init__(self, default_ctx: int, settings: Optional[dict] = None, parent=None):
        super().__init__(parent)
        self.settings = settings or {}
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

        # MCP panels will be created per server below
        self.mcp_panels: list[McpInfoPanel] = []

        # LMS toggle button (will be placed in Settings header row in ChatWindow)
        self.lms_toggle = QtWidgets.QPushButton("LMS")
        self.lms_toggle.setCheckable(True)
        self.lms_toggle.setChecked(False)  # default OFF
        self.lms_toggle.setToolTip("Toggle LM Studio controls")
        self.lms_toggle.toggled.connect(self._on_lms_toggled)

        self._build_ui()
    
    def _build_ui(self) -> None:
        # Wrap subpanels in a vertical-only scroll area
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QtWidgets.QWidget()
        vbox = QtWidgets.QVBoxLayout(content)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(8)

        # No internal toolbar row; LMS toggle is shown in the outer Settings caption

        vbox.addWidget(self.cpp_panel)
        # LM Studio hidden by default, shown when toggle is ON
        self.lmstudio_panel.setVisible(False)
        vbox.addWidget(self.lmstudio_panel)

        # Create one MCP subpanel per configured server
        servers = self.settings.get("mcp_servers", []) or []
        for srv in servers:
            panel = McpInfoPanel(self.settings, server=srv)
            self.mcp_panels.append(panel)
            vbox.addWidget(panel)

        vbox.addStretch(1)
        scroll.setWidget(content)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(scroll)

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

    def _on_lms_toggled(self, checked: bool) -> None:
        """Show/hide LM Studio subpanel based on toggle state."""
        if self.lmstudio_panel:
            self.lmstudio_panel.setVisible(bool(checked))

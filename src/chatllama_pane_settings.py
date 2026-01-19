import logging
from typing import Optional
from PyQt6 import QtWidgets, QtCore
from chatllama_subpanel_llmsettings import LlmSettingsPanel
from chatllama_subpanel_mcpinfo import McpInfoPanel

logger = logging.getLogger(__name__)


class SettingsPanel(QtWidgets.QFrame):
    """Settings panel stacking local (llama.cpp) and MCP controls (no LM Studio)."""
    
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
        # MCP panels will be created per server below
        self.mcp_panels: list[McpInfoPanel] = []
        self.builtin_mcp_servers: list[dict] = []  # Store built-in MCP configs

        self._build_ui()
    
    def _build_ui(self) -> None:
        # Wrap subpanels in a vertical-only scroll area
        scroll = QtWidgets.QScrollArea()
        scroll.setMinimumWidth(0)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QtWidgets.QWidget()
        content.setMinimumWidth(0)
        vbox = QtWidgets.QVBoxLayout(content)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(8)

        # No internal toolbar row; LMS toggle is shown in the outer Settings caption

        vbox.addWidget(self.cpp_panel)

        # Create one MCP subpanel per configured server
        servers = self.settings.get("mcp_servers", []) or []
        for srv in servers:
            panel = McpInfoPanel(self.settings, server=srv)
            self.mcp_panels.append(panel)
            vbox.addWidget(panel)

        vbox.addStretch(1)
        scroll.setWidget(content)
        logger.debug(f"[SettingsPanel] scroll.sizeHint={scroll.sizeHint()}, content.sizeHint={content.sizeHint()}, cpp_panel.sizeHint={self.cpp_panel.sizeHint()}")
        logger.debug(f"[SettingsPanel] cpp_panel.minimumWidth={self.cpp_panel.minimumWidth()}, content.minimumWidth={content.minimumWidth()}, scroll.minimumWidth={scroll.minimumWidth()}")

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

    # LM Studio removed; no toggle behavior

    def register_builtin_mcp(self, server_config: dict) -> None:
        """Register a built-in MCP server and add it to the UI.
        
        Args:
            server_config: Server configuration dict with name, url, type=builtin
        """
        if not server_config:
            return
        
        # Store config
        self.builtin_mcp_servers.append(server_config)
        
        # Create MCP panel for it
        panel = McpInfoPanel(self.settings, server=server_config)
        self.mcp_panels.append(panel)
        
        # Add to UI - find the scroll content widget and insert before stretch
        scroll = self.findChild(QtWidgets.QScrollArea)
        if scroll and scroll.widget():
            content = scroll.widget()
            layout = content.layout()
            if layout:
                # Insert before the final stretch
                count = layout.count()
                if count > 0 and layout.itemAt(count - 1).spacerItem():
                    layout.insertWidget(count - 1, panel)
                else:
                    layout.addWidget(panel)
        
        logger.info(f"Registered built-in MCP: {server_config.get('name')}")

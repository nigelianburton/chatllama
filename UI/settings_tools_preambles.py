from __future__ import annotations

from PyQt6 import QtCore, QtWidgets

from UI.settiing_mcp_preamble_item import SettingsMcpPreambleItem


class SettingsToolsPreambles(QtWidgets.QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setStyleSheet(
            "QFrame { background: #f9f9ff; border: 1px solid #c6d3e8; border-radius: 6px; }"
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self._toggle_button = QtWidgets.QToolButton()
        self._toggle_button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._toggle_button.setArrowType(QtCore.Qt.ArrowType.RightArrow)
        self._toggle_button.setText("tool preamble")
        self._toggle_button.setCheckable(True)
        self._toggle_button.setChecked(False)
        self._toggle_button.setStyleSheet("font-weight: bold; color: #3a3a3a;")
        self._toggle_button.toggled.connect(self._on_toggled)
        layout.addWidget(self._toggle_button)

        self._content_widget = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(self._content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(6)

        self.general_item = SettingsMcpPreambleItem("General tools preamble")
        content_layout.addWidget(self.general_item)

        self._content_widget.setVisible(False)
        layout.addWidget(self._content_widget)

    def _on_toggled(self, checked: bool) -> None:
        self._content_widget.setVisible(checked)
        self._toggle_button.setArrowType(
            QtCore.Qt.ArrowType.DownArrow if checked else QtCore.Qt.ArrowType.RightArrow
        )

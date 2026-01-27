from __future__ import annotations

from PyQt6 import QtCore, QtWidgets


class SettingsLocalMcps(QtWidgets.QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setStyleSheet(
            "QFrame { background: #eef4ff; border: 1px solid #c6d3e8; border-radius: 6px; }"
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self._toggle_button = QtWidgets.QToolButton()
        self._toggle_button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._toggle_button.setArrowType(QtCore.Qt.ArrowType.RightArrow)
        self._toggle_button.setText("settings local mcps")
        self._toggle_button.setCheckable(True)
        self._toggle_button.setChecked(False)
        self._toggle_button.setStyleSheet("font-weight: bold; color: #3a3a3a;")
        self._toggle_button.toggled.connect(self._on_toggled)
        layout.addWidget(self._toggle_button)

        self._content_widget = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(self._content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)

        mcp_row = QtWidgets.QHBoxLayout()
        mcp_row.setContentsMargins(0, 0, 0, 0)
        mcp_row.setSpacing(8)

        self.folder_label = QtWidgets.QLabel("MCP Folder")
        self.folder_label.setFixedWidth(90)

        self.folder_edit = QtWidgets.QLineEdit()

        self.folder_button = QtWidgets.QToolButton()
        self.folder_button.setFixedSize(24, 24)
        self.folder_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DirOpenIcon))

        mcp_row.addWidget(self.folder_label)
        mcp_row.addWidget(self.folder_edit, 1)
        mcp_row.addWidget(self.folder_button)
        content_layout.addLayout(mcp_row)

        add_row = QtWidgets.QHBoxLayout()
        add_row.setContentsMargins(0, 0, 0, 0)
        add_row.setSpacing(8)

        self.add_local_button = QtWidgets.QPushButton("Add Local")
        self.add_local_button.setFixedWidth(90)

        self.add_file_edit = QtWidgets.QLineEdit()

        self.add_file_button = QtWidgets.QToolButton()
        self.add_file_button.setFixedSize(24, 24)
        self.add_file_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DirOpenIcon))

        add_row.addWidget(self.add_local_button)
        add_row.addWidget(self.add_file_edit, 1)
        add_row.addWidget(self.add_file_button)
        content_layout.addLayout(add_row)

        self.panel = QtWidgets.QScrollArea()
        self.panel.setWidgetResizable(True)
        self.panel.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.panel.setMaximumHeight(640)

        self.panel_container = QtWidgets.QWidget()
        self.panel_layout = QtWidgets.QVBoxLayout(self.panel_container)
        self.panel_layout.setContentsMargins(8, 8, 8, 8)
        self.panel_layout.setSpacing(8)
        self.panel_layout.addStretch(1)

        self.panel.setWidget(self.panel_container)
        content_layout.addWidget(self.panel)

        self._content_widget.setVisible(False)
        layout.addWidget(self._content_widget)

    def _on_toggled(self, checked: bool) -> None:
        self._content_widget.setVisible(checked)
        self._toggle_button.setArrowType(
            QtCore.Qt.ArrowType.DownArrow if checked else QtCore.Qt.ArrowType.RightArrow
        )

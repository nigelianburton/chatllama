from __future__ import annotations

from typing import Callable

from PyQt6 import QtCore, QtWidgets

from constants import MCP_LABEL_WIDTH, MCP_PORT_INPUT_WIDTH, TOGGLE_DISABLED_COLOR, TOGGLE_OFF_COLOR, TOGGLE_ON_COLOR


class BuiltInMcpEntryWidget(QtWidgets.QFrame):
    def __init__(
        self,
        name: str,
        url: str,
        port: str,
        methods: list[str],
        enabled: bool = True,
        on_toggle: Callable[[bool], None] | None = None,
    ) -> None:
        super().__init__()
        self.setStyleSheet("QFrame { border: 1px solid #ccc; background: #fafafa; }")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        toggle_style = (
            f"QToolButton {{ background: {TOGGLE_OFF_COLOR}; padding: 4px 8px; border: 1px solid #999; color: #b00020; }}"
            f"QToolButton:checked {{ background: {TOGGLE_ON_COLOR}; color: #000000; }}"
            f"QToolButton:disabled {{ background: {TOGGLE_DISABLED_COLOR}; color: #777; }}"
        )

        toggle = QtWidgets.QToolButton()
        toggle.setCheckable(True)
        toggle.setChecked(enabled)
        toggle.setStyleSheet(toggle_style)

        def update_toggle_text(checked: bool) -> None:
            toggle.setText("✓" if checked else "✗")

        update_toggle_text(enabled)

        name_label = QtWidgets.QLabel(name)
        name_label.setStyleSheet("font-weight: bold;")

        http_label = QtWidgets.QLabel("http")
        http_label.setStyleSheet("padding: 2px 6px; border: 1px solid #999; background: #f0f0f0;")

        row.addWidget(toggle)
        row.addWidget(name_label, 1)
        row.addWidget(http_label)
        layout.addLayout(row)

        def handle_toggle_change(checked: bool) -> None:
            update_toggle_text(checked)
            if on_toggle:
                on_toggle(checked)

        toggle.toggled.connect(handle_toggle_change)

        http_row = QtWidgets.QHBoxLayout()
        http_row.setContentsMargins(0, 0, 0, 0)
        http_row.setSpacing(6)

        url_label = QtWidgets.QLabel("URL")
        port_label = QtWidgets.QLabel("PORT")
        url_label.setMinimumWidth(MCP_LABEL_WIDTH)
        port_label.setMinimumWidth(MCP_LABEL_WIDTH)

        url_edit = QtWidgets.QLineEdit(url)
        url_edit.setReadOnly(True)

        port_edit = QtWidgets.QLineEdit(port)
        port_edit.setReadOnly(True)
        port_edit.setFixedWidth(MCP_PORT_INPUT_WIDTH)

        http_row.addWidget(url_label)
        http_row.addWidget(url_edit, 1)
        http_row.addWidget(port_label)
        http_row.addWidget(port_edit)
        layout.addLayout(http_row)

        methods_container = QtWidgets.QWidget()
        methods_layout = QtWidgets.QHBoxLayout(methods_container)
        methods_layout.setContentsMargins(0, 0, 0, 0)
        methods_layout.setSpacing(6)

        for method in methods:
            badge = QtWidgets.QLabel(method)
            badge.setStyleSheet("padding: 2px 6px; border: 1px solid #bbb; background: #f7f7f7;")
            methods_layout.addWidget(badge)

        layout.addWidget(methods_container)


class SettingsBuiltInMcps(QtWidgets.QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setStyleSheet(
            "QFrame { background: #eef4ff; border: 1px solid #c6d3e8; border-radius: 6px; }"
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.title_label = QtWidgets.QLabel("settings built in mcps")
        self.title_label.setStyleSheet("font-weight: bold; color: #3a3a3a;")
        layout.addWidget(self.title_label)

        self.panel = QtWidgets.QScrollArea()
        self.panel.setWidgetResizable(True)
        self.panel.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.panel.setMaximumHeight(480)

        self.panel_container = QtWidgets.QWidget()
        self.panel_layout = QtWidgets.QVBoxLayout(self.panel_container)
        self.panel_layout.setContentsMargins(8, 8, 8, 8)
        self.panel_layout.setSpacing(8)
        self.panel_layout.addStretch(1)

        self.panel.setWidget(self.panel_container)
        layout.addWidget(self.panel)

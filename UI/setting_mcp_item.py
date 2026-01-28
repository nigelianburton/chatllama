from __future__ import annotations

from pathlib import Path
from typing import Callable

from PyQt6 import QtWidgets

from constants import MCP_LABEL_WIDTH, MCP_PORT_INPUT_WIDTH
from UI.ui_constants import TOGGLE_DISABLED_COLOR, TOGGLE_OFF_COLOR, TOGGLE_ON_COLOR


class SettingsMcpItem(QtWidgets.QFrame):
    def __init__(
        self,
        name: str,
        path: Path | None,
        enabled: bool,
        transport: str,
        url: str,
        port: str,
        on_delete: Callable[[], None],
        show_transport_controls: bool = True,
        show_connection_fields: bool = True,
        show_delete_button: bool = True,
    ) -> None:
        super().__init__()
        self.path = path
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

        self.toggle = QtWidgets.QToolButton()
        self.toggle.setCheckable(True)
        self.toggle.setChecked(enabled)
        self.toggle.setStyleSheet(toggle_style)

        self.name_label = QtWidgets.QLabel(name)
        self.name_label.setStyleSheet("font-weight: bold;")

        self.stdio_radio = QtWidgets.QToolButton()
        self.stdio_radio.setText("stdio")
        self.stdio_radio.setCheckable(True)
        self.stdio_radio.setStyleSheet(toggle_style)

        self.http_radio = QtWidgets.QToolButton()
        self.http_radio.setText("http")
        self.http_radio.setCheckable(True)
        self.http_radio.setStyleSheet(toggle_style)

        transport_group = QtWidgets.QButtonGroup(self)
        transport_group.setExclusive(True)
        transport_group.addButton(self.stdio_radio)
        transport_group.addButton(self.http_radio)

        if transport == "http":
            self.http_radio.setChecked(True)
        else:
            self.stdio_radio.setChecked(True)

        self.delete_button = QtWidgets.QToolButton()
        self.delete_button.setText("✕")
        self.delete_button.setFixedWidth(22)
        self.delete_button.clicked.connect(on_delete)

        row.addWidget(self.toggle)
        row.addWidget(self.name_label, 1)
        if show_transport_controls:
            row.addWidget(self.stdio_radio)
            row.addWidget(self.http_radio)
        if show_delete_button:
            row.addWidget(self.delete_button)
        layout.addLayout(row)

        http_row = QtWidgets.QHBoxLayout()
        http_row.setContentsMargins(0, 0, 0, 0)
        http_row.setSpacing(6)
        self.url_label = QtWidgets.QLabel("URL")
        self.port_label = QtWidgets.QLabel("PORT")
        self.url_edit = QtWidgets.QLineEdit(url)
        self.port_edit = QtWidgets.QLineEdit(str(port))
        self.port_edit.setFixedWidth(MCP_PORT_INPUT_WIDTH)
        self.url_label.setMinimumWidth(MCP_LABEL_WIDTH)
        self.port_label.setMinimumWidth(MCP_LABEL_WIDTH)
        http_row.addWidget(self.url_label)
        http_row.addWidget(self.url_edit, 1)
        http_row.addWidget(self.port_label)
        http_row.addWidget(self.port_edit)
        layout.addLayout(http_row)

        methods_container = QtWidgets.QWidget()
        self.methods_layout = QtWidgets.QHBoxLayout(methods_container)
        self.methods_layout.setContentsMargins(0, 0, 0, 0)
        self.methods_layout.setSpacing(6)
        layout.addWidget(methods_container)

        self.preamble_edit = QtWidgets.QPlainTextEdit()
        self.preamble_edit.setReadOnly(True)
        self.preamble_edit.setMaximumHeight(92)
        self.preamble_edit.setVisible(False)
        layout.addWidget(self.preamble_edit)

        self.update_toggle_text(enabled)
        self.update_http_visibility()
        if not show_transport_controls:
            self.stdio_radio.setVisible(False)
            self.http_radio.setVisible(False)
        if not show_connection_fields:
            self.url_label.setVisible(False)
            self.url_edit.setVisible(False)
            self.port_label.setVisible(False)
            self.port_edit.setVisible(False)
        if not show_delete_button:
            self.delete_button.setVisible(False)

    def update_toggle_text(self, checked: bool) -> None:
        self.toggle.setText("✓" if checked else "✗")

    def update_http_visibility(self) -> None:
        http_visible = self.http_radio.isChecked()
        self.url_label.setVisible(http_visible)
        self.url_edit.setVisible(http_visible)
        self.port_label.setVisible(http_visible)
        self.port_edit.setVisible(http_visible)

    def set_preamble(self, text: str | None) -> None:
        if text:
            self.preamble_edit.setPlainText(text)
            self.preamble_edit.setVisible(True)
        else:
            self.preamble_edit.setVisible(False)

    def set_methods_badges(self, methods: list[str]) -> None:
        layout = self.methods_layout
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget() if item else None
            if widget:
                widget.deleteLater()
        for method in methods:
            badge = QtWidgets.QLabel(method)
            badge.setStyleSheet("padding: 2px 6px; border: 1px solid #bbb; background: #f7f7f7;")
            layout.addWidget(badge)

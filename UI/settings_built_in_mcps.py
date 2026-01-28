from __future__ import annotations

from typing import Callable

from PyQt6 import QtCore, QtWidgets

from UI.ui_constants import (
    ACCORDION_COLLAPSED_BG_COLOR,
    ACCORDION_COLLAPSED_TEXT_COLOR,
    ACCORDION_EXPANDED_BG_COLOR,
    ACCORDION_EXPANDED_TEXT_COLOR,
    TOGGLE_DISABLED_COLOR,
    TOGGLE_OFF_COLOR,
    TOGGLE_ON_COLOR,
)


class BuiltInMcpEntryWidget(QtWidgets.QFrame):
    def __init__(
        self,
        name: str,
        methods: list[str],
        preamble: str | None,
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

        row.addWidget(toggle)
        row.addWidget(name_label, 1)
        layout.addLayout(row)

        def handle_toggle_change(checked: bool) -> None:
            update_toggle_text(checked)
            if on_toggle:
                on_toggle(checked)

        toggle.toggled.connect(handle_toggle_change)

        methods_container = QtWidgets.QWidget()
        methods_layout = QtWidgets.QHBoxLayout(methods_container)
        methods_layout.setContentsMargins(0, 0, 0, 0)
        methods_layout.setSpacing(6)

        for method in methods:
            badge = QtWidgets.QLabel(method)
            badge.setStyleSheet("padding: 2px 6px; border: 1px solid #bbb; background: #f7f7f7;")
            methods_layout.addWidget(badge)

        layout.addWidget(methods_container)

        preamble_edit = QtWidgets.QPlainTextEdit()
        preamble_edit.setReadOnly(True)
        preamble_edit.setMaximumHeight(92)
        if preamble:
            preamble_edit.setPlainText(preamble)
            preamble_edit.setVisible(True)
        else:
            preamble_edit.setVisible(False)
        layout.addWidget(preamble_edit)


class SettingsBuiltInMcps(QtWidgets.QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setStyleSheet(
            "QFrame { background: #eef4ff; border: 1px solid #c6d3e8; border-radius: 6px; }"
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self._toggle_button = QtWidgets.QToolButton()
        header_row = QtWidgets.QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        self._toggle_button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._toggle_button.setArrowType(QtCore.Qt.ArrowType.RightArrow)
        self._toggle_button.setText("settings built in mcps")
        self._toggle_button.setCheckable(True)
        self._toggle_button.setChecked(False)
        self._toggle_button.toggled.connect(self._on_toggled)
        self._apply_toggle_style(self._toggle_button.isChecked())
        header_row.addWidget(self._toggle_button)

        header_row.addStretch(1)

        self._endpoint_label = QtWidgets.QLabel("")
        self._endpoint_label.setStyleSheet("color: #5a5a5a;")
        header_row.addWidget(self._endpoint_label)

        layout.addLayout(header_row)

        self._content_widget = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(self._content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)

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
        content_layout.addWidget(self.panel)

        self._content_widget.setVisible(False)
        layout.addWidget(self._content_widget)

    def _on_toggled(self, checked: bool) -> None:
        self._content_widget.setVisible(checked)
        self._toggle_button.setArrowType(
            QtCore.Qt.ArrowType.DownArrow if checked else QtCore.Qt.ArrowType.RightArrow
        )
        self._apply_toggle_style(checked)

    def _apply_toggle_style(self, expanded: bool) -> None:
        text_color = ACCORDION_EXPANDED_TEXT_COLOR if expanded else ACCORDION_COLLAPSED_TEXT_COLOR
        bg_color = ACCORDION_EXPANDED_BG_COLOR if expanded else ACCORDION_COLLAPSED_BG_COLOR
        self._toggle_button.setStyleSheet(
            f"QToolButton {{ font-weight: bold; color: {text_color}; background: {bg_color}; }}"
        )

    def set_endpoint(self, ip: str, port: str) -> None:
        self._endpoint_label.setText(f"{ip}:{port}")

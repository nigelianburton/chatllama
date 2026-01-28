from __future__ import annotations

from PyQt6 import QtCore, QtWidgets

from UI.ui_constants import (
    ACCORDION_COLLAPSED_BG_COLOR,
    ACCORDION_COLLAPSED_TEXT_COLOR,
    ACCORDION_EXPANDED_BG_COLOR,
    ACCORDION_EXPANDED_TEXT_COLOR,
)


class SettingLog(QtWidgets.QFrame):
    log_appended = QtCore.pyqtSignal(str)

    def __init__(self, label: str = "setting_log") -> None:
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
        self._toggle_button.setText(label)
        self._toggle_button.setCheckable(True)
        self._toggle_button.setChecked(False)
        self._toggle_button.toggled.connect(self._on_toggled)
        self._apply_toggle_style(self._toggle_button.isChecked())
        layout.addWidget(self._toggle_button)

        self._content_widget = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(self._content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)

        self.text_edit = QtWidgets.QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setMaximumHeight(256)
        self.text_edit.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.text_edit.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.text_edit.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        content_layout.addWidget(self.text_edit)

        self._content_widget.setVisible(False)
        layout.addWidget(self._content_widget)

        self.log_appended.connect(self._append_line)

    def append_line(self, text: str) -> None:
        self.log_appended.emit(text)

    def _append_line(self, text: str) -> None:
        self.text_edit.appendPlainText(text)

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

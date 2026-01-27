from __future__ import annotations

from PyQt6 import QtCore, QtWidgets


class SettingsMcpPreambleItem(QtWidgets.QFrame):
    def __init__(self, label: str) -> None:
        super().__init__()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        header_row = QtWidgets.QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        self.label = QtWidgets.QLabel(label)
        header_row.addWidget(self.label)
        header_row.addStretch(1)

        self.save_button = QtWidgets.QPushButton("Save")
        self.save_button.setFixedWidth(80)
        header_row.addWidget(self.save_button)

        layout.addLayout(header_row)

        self.text_edit = QtWidgets.QPlainTextEdit()
        self.text_edit.setMaximumHeight(92)
        layout.addWidget(self.text_edit)

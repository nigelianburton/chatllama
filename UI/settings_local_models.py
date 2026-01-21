from __future__ import annotations

from PyQt6 import QtCore, QtWidgets


class SettingsLocalModels(QtWidgets.QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setStyleSheet(
            "QFrame { background: #eef4ff; border: 1px solid #c6d3e8; border-radius: 6px; }"
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.title_label = QtWidgets.QLabel("settings_local_models")
        self.title_label.setStyleSheet("font-weight: bold; color: #3a3a3a;")
        layout.addWidget(self.title_label)

        self.status_label = QtWidgets.QLabel("Model: None")
        self.status_label.setStyleSheet("color: #1c7c1c; font-weight: bold;")
        self.status_label.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Ignored,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self.status_label.setMinimumWidth(0)
        self.status_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.status_label)

        top_row = QtWidgets.QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        self.model_combo = QtWidgets.QComboBox()
        self.model_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.model_combo.setMinimumContentsLength(0)
        self.model_combo.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self.model_combo.setEnabled(False)

        self.load_button = QtWidgets.QPushButton("Load")
        self.load_button.setEnabled(False)

        top_row.addWidget(self.model_combo, 1)
        top_row.addWidget(self.load_button)
        layout.addLayout(top_row)

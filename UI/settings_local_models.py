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

        self._toggle_button = QtWidgets.QToolButton()
        self._toggle_button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._toggle_button.setArrowType(QtCore.Qt.ArrowType.RightArrow)
        self._toggle_button.setText("settings_local_models")
        self._toggle_button.setCheckable(True)
        self._toggle_button.setChecked(False)
        self._toggle_button.setStyleSheet("font-weight: bold; color: #3a3a3a;")
        self._toggle_button.toggled.connect(self._on_toggled)
        layout.addWidget(self._toggle_button)

        self._content_widget = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(self._content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)

        self.status_label = QtWidgets.QLabel("Model: None")
        self.status_label.setStyleSheet("color: #1c7c1c; font-weight: bold;")
        self.status_label.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Ignored,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self.status_label.setMinimumWidth(0)
        self.status_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        content_layout.addWidget(self.status_label)

        top_row = QtWidgets.QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        self.model_combo = QtWidgets.QComboBox()
        self.model_combo.setSizeAdjustPolicy(
            QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
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
        content_layout.addLayout(top_row)

        self._content_widget.setVisible(False)
        layout.addWidget(self._content_widget)

    def _on_toggled(self, checked: bool) -> None:
        self._content_widget.setVisible(checked)
        self._toggle_button.setArrowType(
            QtCore.Qt.ArrowType.DownArrow if checked else QtCore.Qt.ArrowType.RightArrow
        )

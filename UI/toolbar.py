from __future__ import annotations

from PyQt6 import QtCore, QtWidgets

from UI.ui_constants import TOOLBAR_BG_COLOR, TOOLBAR_HEIGHT


class MainToolbarWidget(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._toolbar = QtWidgets.QToolBar()
        self._toolbar.setMovable(False)
        self._toolbar.setFixedHeight(TOOLBAR_HEIGHT)
        self._toolbar.setStyleSheet(f"background-color: {TOOLBAR_BG_COLOR};")

        self.model_title_label = QtWidgets.QLabel("Model: None")
        self.model_title_label.setStyleSheet("font-weight: bold;")
        self._toolbar.addWidget(self.model_title_label)

        toolbar_spacer = QtWidgets.QWidget()
        toolbar_spacer.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        self._toolbar.addWidget(toolbar_spacer)

        self.status_label = QtWidgets.QLabel("50%")
        self.status_label.setFixedWidth(50)
        self.status_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self.status_label.setVisible(False)
        self._toolbar.addWidget(self.status_label)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setFixedWidth(150)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self._toolbar.addWidget(self.progress_bar)

        layout.addWidget(self._toolbar)

    def add_toggle_button(self, button: QtWidgets.QToolButton) -> None:
        self._toolbar.addWidget(button)

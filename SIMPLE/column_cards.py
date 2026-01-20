from __future__ import annotations

from PyQt6 import QtWidgets

from logger import get_logger


class ColumnCardsWidget(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._logger = get_logger(self)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.addStretch(1)

        self._layout = layout

    @property
    def cards_layout(self) -> QtWidgets.QVBoxLayout:
        return self._layout

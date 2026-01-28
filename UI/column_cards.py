from __future__ import annotations

from PyQt6 import QtCore, QtWidgets

from Engine.logger import get_logger
from UI.ui_constants import TOGGLE_OFF_COLOR, TOGGLE_ON_COLOR


class ColumnCardsWidget(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._logger = get_logger(self)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        self._auto_scroll_toggle = QtWidgets.QToolButton()
        self._auto_scroll_toggle.setText("Auto-scroll")
        self._auto_scroll_toggle.setCheckable(True)
        self._auto_scroll_toggle.setChecked(True)
        self._auto_scroll_toggle.setStyleSheet(
            f"QToolButton {{ background: {TOGGLE_OFF_COLOR}; padding: 4px; }}"
            f"QToolButton:checked {{ background: {TOGGLE_ON_COLOR}; }}"
        )
        self._auto_scroll_toggle.toggled.connect(self._on_auto_scroll_toggled)

        caption_row = QtWidgets.QHBoxLayout()
        caption_row.setContentsMargins(0, 0, 0, 0)
        caption_row.setSpacing(8)
        caption_label = QtWidgets.QLabel("Cards")
        caption_label.setStyleSheet("font-weight: bold;")
        caption_row.addWidget(caption_label)
        caption_row.addStretch(1)
        caption_row.addWidget(self._auto_scroll_toggle)
        layout.addLayout(caption_row)

        self._cards_container = QtWidgets.QWidget()
        self._cards_layout = QtWidgets.QVBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(8, 8, 8, 8)
        self._cards_layout.setSpacing(8)
        self._cards_layout.addStretch(1)
        self._cards_container.installEventFilter(self)

        self._cards_scroll = QtWidgets.QScrollArea()
        self._cards_scroll.setWidgetResizable(True)
        self._cards_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._cards_scroll.setWidget(self._cards_container)
        self._cards_scroll.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        layout.addWidget(self._cards_scroll, 1)

    @property
    def cards_layout(self) -> QtWidgets.QVBoxLayout:
        return self._cards_layout

    def eventFilter(self, source: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if source is self._cards_container and event.type() == QtCore.QEvent.Type.LayoutRequest:
            QtCore.QTimer.singleShot(0, self._maybe_scroll_to_bottom)
        return super().eventFilter(source, event)

    def _on_auto_scroll_toggled(self, checked: bool) -> None:
        if checked:
            self._maybe_scroll_to_bottom()

    def _maybe_scroll_to_bottom(self) -> None:
        if not self._auto_scroll_toggle.isChecked():
            return
        bar = self._cards_scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

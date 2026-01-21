from __future__ import annotations

from typing import Optional

from PyQt6 import QtCore, QtGui, QtWidgets, QtSvgWidgets

from Engine.logger import get_logger


class SVGCard(QtWidgets.QFrame):
    def __init__(self, guid: str, is_portrait: bool) -> None:
        super().__init__()
        self._logger = get_logger(self)
        self.guid = guid
        self.is_portrait = is_portrait

        width, height = (480, 640) if is_portrait else (640, 480)
        self._aspect_ratio = height / width
        self._parent_filter_installed = False
        self.setSizePolicy(
            QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        )
        self.setStyleSheet("background-color: white; border: 1px solid #999;")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._view = QtSvgWidgets.QSvgWidget(self)
        self._view.setSizePolicy(
            QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        )
        layout.addWidget(self._view)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._sync_height_to_width()

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        self._install_parent_filter()
        self._sync_height_to_width()

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.Type.Resize:
            self._sync_height_to_width()
        return super().eventFilter(obj, event)

    def sizeHint(self) -> QtCore.QSize:
        width = 480
        height = int(width * self._aspect_ratio)
        return QtCore.QSize(width, height)

    def _install_parent_filter(self) -> None:
        if self._parent_filter_installed:
            return
        parent = self.parentWidget()
        if parent is not None:
            parent.installEventFilter(self)
            self._parent_filter_installed = True

    def _sync_height_to_width(self) -> None:
        width = max(self._available_width() - 2, 1)
        height = int(width * self._aspect_ratio)
        if self.height() != height:
            self.setFixedHeight(height)

    def _available_width(self) -> int:
        parent = self.parentWidget()
        if parent is None:
            return self.width()
        width = parent.width()
        layout = parent.layout()
        if layout is not None:
            margins = layout.contentsMargins()
            width -= (margins.left() + margins.right())
        return max(width, 1)

    def load_svg_content(self, svg: str) -> None:
        if not svg:
            self._logger.warning("Empty SVG content for card %s", self.guid)
            return
        self._view.load(QtCore.QByteArray(svg.encode("utf-8")))

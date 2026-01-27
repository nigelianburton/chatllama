from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from PyQt6 import QtCore, QtWidgets

from UI.column_chat import ChatColumnWidget
from UI.column_cards import ColumnCardsWidget
from UI.column_settings import ColumnSettingsWidget
from constants import TOGGLE_OFF_COLOR, TOGGLE_ON_COLOR
from Engine.logger import get_logger


class ColumnPanel(QtWidgets.QFrame):
    def __init__(
        self,
        title: str,
        color: str,
        content_widget: Optional[QtWidgets.QWidget] = None,
        header_color: Optional[str] = None,
    ) -> None:
        super().__init__()
        self._logger = get_logger(self)

        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"background-color: {color};")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._toolbar = QtWidgets.QToolBar()
        self._toolbar.setIconSize(QtCore.QSize(16, 16))
        self._toolbar.setMovable(False)
        self._toolbar.setStyleSheet(f"background-color: {header_color or color};")

        title_label = QtWidgets.QLabel(title)
        title_label.setStyleSheet("font-weight: bold; padding: 4px;")

        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)

        self._toolbar.addWidget(title_label)
        self._toolbar.addWidget(spacer)

        layout.addWidget(self._toolbar)

        if content_widget is None:
            content = QtWidgets.QLabel(f"{title} content")
            content.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            content_widget = content
        layout.addWidget(content_widget, 1)

    def set_header_color(self, color: str) -> None:
        self._toolbar.setStyleSheet(f"background-color: {color};")


class MainPageWidget(QtWidgets.QWidget):
    def __init__(self, settings_folder: Path) -> None:
        super().__init__()
        self._logger = get_logger(self)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        top_toolbar = QtWidgets.QToolBar()
        top_toolbar.setMovable(False)
        self.model_title_label = QtWidgets.QLabel("Model: None")
        self.model_title_label.setStyleSheet("font-weight: bold;")
        top_toolbar.addWidget(self.model_title_label)

        toolbar_spacer = QtWidgets.QWidget()
        toolbar_spacer.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred
        )
        top_toolbar.addWidget(toolbar_spacer)

        self.status_label = QtWidgets.QLabel("50%")
        self.status_label.setFixedWidth(50)
        self.status_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.status_label.setVisible(False)
        top_toolbar.addWidget(self.status_label)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setFixedWidth(150)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        top_toolbar.addWidget(self.progress_bar)
        self.top_toolbar = top_toolbar
        main_layout.addWidget(top_toolbar)

        self._toggle_style = (
            f"QToolButton {{ background: {TOGGLE_OFF_COLOR}; padding: 4px; }}"
            f"QToolButton:checked {{ background: {TOGGLE_ON_COLOR}; }}"
        )

        self._splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        main_layout.addWidget(self._splitter, 1)

        self._columns: Dict[str, QtWidgets.QWidget] = {}
        self._column_visible: Dict[str, bool] = {}
        self._toggle_buttons: Dict[str, QtWidgets.QToolButton] = {}

        self.settings_container = ColumnSettingsWidget(settings_folder)
        self._add_column("Settings", "#f7e0e0", content_widget=self.settings_container)

        self.chat_container = ChatColumnWidget()
        self._add_column("Chat", "#e0f7e0", content_widget=self.chat_container)

        self.cards_container = ColumnCardsWidget()
        self.cards_layout = self.cards_container.cards_layout
        self._add_column("Cards", "#e0e8f7", content_widget=self.cards_container)

        self._apply_splitter_sizes()

    def set_column_header_color(self, name: str, color: str) -> None:
        panel = self._columns.get(name)
        if isinstance(panel, ColumnPanel):
            panel.set_header_color(color)

    def _add_column(
        self,
        name: str,
        color: str,
        content_widget: Optional[QtWidgets.QWidget] = None,
        header_color: Optional[str] = None,
    ) -> None:
        def on_toggle(checked: bool) -> None:
            self._column_visible[name] = checked
            widget = self._columns[name]
            widget.setVisible(checked)
            self._apply_splitter_sizes()

        panel = ColumnPanel(name, color, content_widget=content_widget, header_color=header_color)
        self._splitter.addWidget(panel)
        self._columns[name] = panel
        self._column_visible[name] = True

        toggle = QtWidgets.QToolButton()
        toggle.setText(name)
        toggle.setCheckable(True)
        toggle.setChecked(True)
        toggle.setStyleSheet(self._toggle_style)
        toggle.clicked.connect(lambda checked, n=name: on_toggle(checked))
        self.top_toolbar.addWidget(toggle)
        self._toggle_buttons[name] = toggle

    def _apply_splitter_sizes(self) -> None:
        visible = [name for name, is_on in self._column_visible.items() if is_on]
        if not visible:
            sizes = [0 for _ in self._columns]
        else:
            per = int(1000 / len(visible))
            sizes = [per if self._column_visible[name] else 0 for name in self._columns]
        self._splitter.setSizes(sizes)

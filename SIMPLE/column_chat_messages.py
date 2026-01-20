from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, Sequence

from PyQt6 import QtCore, QtGui, QtWidgets

from logger import get_logger


class MessageType(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    MCP_REQUEST = "mcp_request"
    MCP_UI_REQUEST = "mcp_ui_request"
    THINKING = "thinking"
    MCP_RESPONSE = "mcp_response"
    MCP_UI_RESPONSE = "mcp_ui_response"
    ERROR = "error"
    PROGRESS = "progress"


@dataclass(frozen=True)
class MessageStyle:
    label: str
    fill: str


MESSAGE_STYLES: dict[MessageType, MessageStyle] = {
    MessageType.USER: MessageStyle(label="User", fill="#f7f2ff"),
    MessageType.ASSISTANT: MessageStyle(label="Assistant", fill="#e8f1ff"),
    MessageType.MCP_REQUEST: MessageStyle(label="MCP Request", fill="#fff2cc"),
    MessageType.MCP_UI_REQUEST: MessageStyle(label="MCP UI Request", fill="#fbe4ff"),
    MessageType.THINKING: MessageStyle(label="Thinking", fill="#f5f5f5"),
    MessageType.MCP_RESPONSE: MessageStyle(label="MCP Response", fill="#eaf7ea"),
    MessageType.MCP_UI_RESPONSE: MessageStyle(label="MCP UI Response", fill="#e6f7ff"),
    MessageType.ERROR: MessageStyle(label="Error", fill="#ffe0e0"),
    MessageType.PROGRESS: MessageStyle(label="Progress", fill="#fff0f5"),
}


class MessageBubble(QtWidgets.QFrame):
    def __init__(
        self,
        message_type: MessageType,
        text: str,
        attachments: Iterable[Path] | None = None,
        details: Sequence[tuple[str, str]] | None = None,
    ) -> None:
        super().__init__()
        self._logger = get_logger(self)
        self._message_type = message_type
        self._attachments = list(attachments) if attachments else []
        self._message_label: QtWidgets.QLabel | None = None

        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)

        style = MESSAGE_STYLES.get(message_type, MessageStyle(label=str(message_type), fill="#f2f2f2"))

        outer_layout = QtWidgets.QGridLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        border = QtWidgets.QFrame()
        border.setStyleSheet(
            "QFrame {"
            "border: 2px solid #000;"
            f"background-color: {style.fill};"
            "border-radius: 5px;"
            "}"
        )
        border_layout = QtWidgets.QVBoxLayout(border)
        border_layout.setContentsMargins(3, 17, 3, 3)
        border_layout.setSpacing(6)

        content_row = QtWidgets.QHBoxLayout()
        content_row.setContentsMargins(0, 0, 0, 0)
        content_row.setSpacing(6)

        message = QtWidgets.QLabel(text)
        message.setWordWrap(True)
        message.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
        message.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        content_row.addWidget(message, 1)
        self._message_label = message

        attachments_widget = self._build_attachments_widget()
        if attachments_widget is not None:
            content_row.addWidget(attachments_widget, 0, QtCore.Qt.AlignmentFlag.AlignRight)

        border_layout.addLayout(content_row)

        self._details_container = QtWidgets.QFrame()
        self._details_container.setStyleSheet("QFrame { background: transparent; }")
        details_layout = QtWidgets.QGridLayout(self._details_container)
        details_layout.setContentsMargins(3, 3, 3, 3)
        details_layout.setHorizontalSpacing(6)
        details_layout.setVerticalSpacing(3)
        self._details_layout = details_layout
        self._details_container.setVisible(False)
        border_layout.addWidget(self._details_container)

        if details:
            self.set_details(details)

        outer_layout.addWidget(border, 0, 0)

        label = QtWidgets.QLabel(style.label)
        label.setStyleSheet("background-color: #ffffff; font-size: 8pt; padding: 3px;")
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        label.setFixedHeight(20)
        outer_layout.addWidget(label, 0, 0, QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft)

    def append_text(self, text: str) -> None:
        if not self._message_label:
            return
        self._message_label.setText(self._message_label.text() + text)

    def get_text(self) -> str:
        if not self._message_label:
            return ""
        return self._message_label.text()

    def set_details(self, rows: Sequence[tuple[str, str]]) -> None:
        while self._details_layout.count():
            item = self._details_layout.takeAt(0)
            widget = item.widget() if item else None
            if widget:
                widget.deleteLater()

        for row_index, (key, value) in enumerate(rows):
            key_label = QtWidgets.QLabel(str(key))
            key_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
            value_label = QtWidgets.QLabel(str(value))
            value_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
            value_label.setWordWrap(True)
            self._details_layout.addWidget(key_label, row_index, 0)
            self._details_layout.addWidget(value_label, row_index, 1)

    def set_details_visible(self, visible: bool) -> None:
        self._details_container.setVisible(visible)

    def _build_attachments_widget(self) -> QtWidgets.QWidget | None:
        if not self._attachments:
            return None

        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addStretch(1)

        for path in self._attachments:
            frame = QtWidgets.QFrame()
            frame_layout = QtWidgets.QVBoxLayout(frame)
            frame_layout.setContentsMargins(3, 3, 3, 3)
            frame_layout.setSpacing(0)

            label = QtWidgets.QLabel()
            label.setFixedSize(32, 32)
            label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("background-color: #e6e6e6;")

            pixmap = QtGui.QPixmap(str(path))
            if pixmap.isNull():
                self._logger.warning("Failed to load attachment image: %s", path)
            else:
                thumb = pixmap.scaled(
                    32,
                    32,
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    QtCore.Qt.TransformationMode.SmoothTransformation,
                )
                label.setPixmap(thumb)

            frame_layout.addWidget(label)
            layout.addWidget(frame)

        return container


def create_message_widget(
    message_type: MessageType,
    text: str,
    attachments: Iterable[Path] | None = None,
    details: Sequence[tuple[str, str]] | None = None,
) -> MessageBubble:
    return MessageBubble(message_type=message_type, text=text, attachments=attachments, details=details)

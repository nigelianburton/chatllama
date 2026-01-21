from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Iterable

import importlib.util

from PyQt6 import QtCore, QtGui, QtWidgets

from Engine.logger import get_logger
from UI.column_chat_messages import MessageType, MessageBubble, create_message_widget
from constants import SHOW_SAMPLE_MESSAGES, TOGGLE_OFF_COLOR, TOGGLE_ON_COLOR


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}


class AttachmentsBar(QtWidgets.QFrame):
    def __init__(self) -> None:
        super().__init__()
        self._logger = get_logger(self)
        self._paths: list[Path] = []
        self.setAcceptDrops(True)
        self.setFixedHeight(48)
        self.setStyleSheet("background-color: #e6e6e6; border: 1px solid #cfcfcf;")

        self._layout = QtWidgets.QHBoxLayout(self)
        self._layout.setContentsMargins(8, 4, 8, 4)
        self._layout.setSpacing(8)
        self._layout.addStretch(1)

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        urls = event.mimeData().urls()
        if not urls:
            return
        paths = [Path(url.toLocalFile()) for url in urls if url.isLocalFile()]
        self._add_images(paths)
        event.acceptProposedAction()

    def _add_images(self, paths: Iterable[Path]) -> None:
        for path in paths:
            if path.suffix.lower() not in IMAGE_EXTS:
                continue
            if not path.exists():
                continue
            pixmap = QtGui.QPixmap(str(path))
            if pixmap.isNull():
                self._logger.warning("Failed to load image: %s", path)
                continue
            thumb = pixmap.scaled(
                40,
                40,
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation,
            )
            label = QtWidgets.QLabel()
            label.setFixedSize(40, 40)
            label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            label.setPixmap(thumb)
            self._layout.insertWidget(self._layout.count() - 1, label)
            self._paths.append(path)

    def add_images(self, paths: Iterable[Path]) -> None:
        self._add_images(paths)

    def get_paths(self) -> list[Path]:
        return list(self._paths)

    def clear(self) -> None:
        self._paths.clear()
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            widget = item.widget() if item else None
            if widget:
                widget.deleteLater()


class ChatColumnWidget(QtWidgets.QWidget):
    model_state_updated = QtCore.pyqtSignal(str)
    stream_chunk_received = QtCore.pyqtSignal(str)
    stream_completed = QtCore.pyqtSignal()
    tool_call_received = QtCore.pyqtSignal(object)
    tool_result_received = QtCore.pyqtSignal(object, object)
    followup_reply_started = QtCore.pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._logger = get_logger(self)
        self._llama_module = None
        self._chat_server = None
        self._current_receive: MessageBubble | None = None
        self._current_receive_pending = False
        self._availability_callbacks: list[Callable[[str], None]] = []
        self._availability_hooked = False
        self._pending_availability: str | None = None
        self._last_availability: str | None = None

        self.model_state_updated.connect(self._update_input_state)
        self.stream_chunk_received.connect(self._append_stream_chunk)
        self.stream_completed.connect(self._finalize_stream_message)
        self.tool_call_received.connect(self._on_tool_call)
        self.tool_result_received.connect(self._on_tool_result)
        self.followup_reply_started.connect(self._on_followup_reply_started)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        caption_row = QtWidgets.QHBoxLayout()
        caption_row.setContentsMargins(0, 0, 0, 0)
        caption_row.setSpacing(8)

        caption_label = QtWidgets.QLabel("History")
        caption_label.setStyleSheet("font-weight: bold;")
        caption_row.addWidget(caption_label)

        caption_row.addStretch(1)

        self._auto_scroll_toggle = QtWidgets.QToolButton()
        self._auto_scroll_toggle.setText("Auto-scroll")
        self._auto_scroll_toggle.setCheckable(True)
        self._auto_scroll_toggle.setChecked(True)
        self._auto_scroll_toggle.setStyleSheet(
            f"QToolButton {{ background: {TOGGLE_OFF_COLOR}; padding: 4px; }}"
            f"QToolButton:checked {{ background: {TOGGLE_ON_COLOR}; }}"
        )
        self._auto_scroll_toggle.toggled.connect(self._on_auto_scroll_toggled)
        caption_row.addWidget(self._auto_scroll_toggle)

        layout.addLayout(caption_row)

        self._history_container = QtWidgets.QWidget()
        self._history_layout = QtWidgets.QVBoxLayout(self._history_container)
        self._history_layout.setContentsMargins(8, 8, 8, 8)
        self._history_layout.setSpacing(8)
        self._history_layout.addStretch(1)

        self._history_scroll = QtWidgets.QScrollArea()
        self._history_scroll.setWidgetResizable(True)
        self._history_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._history_scroll.setStyleSheet("background-color: #dff4d8; border: 1px dashed #999;")
        self._history_scroll.setWidget(self._history_container)
        self._history_scroll.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        layout.addWidget(self._history_scroll, 1)

        layout.addSpacing(8)

        entry_panel = QtWidgets.QFrame()
        entry_panel.setStyleSheet("QFrame { border: none; background: transparent; }")
        entry_panel.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Minimum,
        )

        entry_layout = QtWidgets.QHBoxLayout(entry_panel)
        entry_layout.setContentsMargins(0, 0, 0, 0)
        entry_layout.setSpacing(8)

        self._prompt_box = ChatInputBox()
        self._prompt_box.setPlaceholderText("Type a message...")
        self._prompt_box.setEnabled(False)
        self._prompt_box.setStyleSheet("QTextEdit { border: 2px solid #000; }")
        self._prompt_box.sendRequested.connect(self._on_send_clicked)
        self._prompt_box.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Minimum,
        )

        self._send_button = QtWidgets.QPushButton("Send")
        self._send_button.setFixedWidth(80)
        self._send_button.setEnabled(False)
        self._send_button.clicked.connect(self._on_send_clicked)

        entry_layout.addWidget(self._prompt_box, 1)
        entry_layout.addWidget(self._send_button)

        self._attachments_bar = AttachmentsBar()

        bottom_panel = QtWidgets.QFrame()
        bottom_panel.setStyleSheet("QFrame { background: #fff3a6; }")
        bottom_panel.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Minimum,
        )
        bottom_layout = QtWidgets.QVBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(8, 8, 8, 8)
        bottom_layout.setSpacing(8)
        bottom_layout.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetMinimumSize)
        bottom_layout.addWidget(entry_panel)
        bottom_layout.addWidget(self._attachments_bar)

        layout.addWidget(bottom_panel)

        if SHOW_SAMPLE_MESSAGES:
            self._add_sample_messages()

        self._register_model_state()

    def _add_message(self, widget: MessageBubble) -> None:
        self._history_layout.insertWidget(self._history_layout.count() - 1, widget)
        self._maybe_scroll_to_bottom()

    def _remove_message(self, widget: MessageBubble) -> None:
        self._history_layout.removeWidget(widget)
        widget.log_removed()
        widget.deleteLater()

    def _add_sample_messages(self) -> None:
        resources_dir = Path(__file__).resolve().parents[1] / "resources"
        samples = [
            (MessageType.USER, "User message example."),
            (MessageType.ASSISTANT, "Assistant response example."),
            (MessageType.TOOLS_ADVERTISEMENT, "Tools Advertisement (2 tools)"),
            (MessageType.MCP_REQUEST, "tool.weather.get_forecast"),
            (MessageType.MCP_UI_REQUEST, "SVGCard.DrawCard"),
            (MessageType.THINKING, "Assistant thinking example..."),
            (MessageType.MCP_RESPONSE, "External MCP response example."),
            (MessageType.MCP_UI_RESPONSE, "Internal MCP UI response example."),
            (MessageType.ERROR, "Error example: something went wrong."),
            (MessageType.PROGRESS, "Progress example: loading model..."),
        ]
        for msg_type, text in samples:
            bubble = create_message_widget(msg_type, text)
            if msg_type == MessageType.MCP_REQUEST:
                bubble.set_details(
                    [
                        ("location", "Seattle"),
                        ("units", "metric"),
                        ("days", "3"),
                    ]
                )
                bubble.set_details_visible(True)
            if msg_type == MessageType.MCP_UI_REQUEST:
                bubble.set_details(
                    [
                        ("svg", "<svg width='512' height='512'>...</svg>"),
                    ]
                )
                bubble.set_details_visible(True)
            if msg_type == MessageType.MCP_RESPONSE:
                bubble.set_details(
                    [
                        ("temperature", "12°C"),
                        ("condition", "Light rain"),
                        ("wind", "8 km/h"),
                    ]
                )
                bubble.set_details_visible(True)
            self._add_message(bubble)

        attachments = [
            resources_dir / "pic1-portrait.jpg",
            resources_dir / "pic2-landscape.jpg",
        ]
        self._add_message(
            create_message_widget(
                MessageType.USER,
                "User message with two image attachments.",
                attachments=attachments,
            )
        )

    def _register_model_state(self) -> None:
        module_path = Path(__file__).parent.parent / "Engine" / "manager_models.py"
        spec = importlib.util.spec_from_file_location("manager_models", module_path)
        if spec is None or spec.loader is None:
            self._logger.error("Failed to load llamacpp-server module")
            return
        import sys
        model_module = sys.modules.get(spec.name)
        if model_module is None:
            model_module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = model_module
            spec.loader.exec_module(model_module)

        self._llama_module = model_module

        chat_module_path = Path(__file__).parent.parent / "Engine" / "manager_chats.py"
        chat_spec = importlib.util.spec_from_file_location("manager_chats", chat_module_path)
        if chat_spec is None or chat_spec.loader is None:
            self._logger.error("Failed to load chat manager module")
            return
        chat_module = sys.modules.get(chat_spec.name)
        if chat_module is None:
            chat_module = importlib.util.module_from_spec(chat_spec)
            sys.modules[chat_spec.name] = chat_module
            chat_spec.loader.exec_module(chat_module)

        try:
            self._chat_server = chat_module.LlamaChatManager()
            self._chat_server.register_stream_callback(self._on_stream_chunk)
            self._chat_server.register_stream_end_callback(self._on_stream_end)
            self._chat_server.register_tool_call_callback(self._on_tool_call_callback)
            self._chat_server.register_tool_result_callback(self._on_tool_result_callback)
            self._chat_server.register_followup_callback(self._on_followup_callback)
            self._chat_server.register_availability_callback(self._on_chat_availability)
            self._availability_hooked = True
        except Exception as exc:
            self._logger.exception("Failed to initialize chat server: %s", exc)
            self._chat_server = None
        model_module.register_model_state_callback(self._on_model_state)

    def _on_model_state(self, state: str, _model_name: str | None) -> None:
        self.model_state_updated.emit(state)

    def _update_input_state(self, state: str) -> None:
        ready = state == "Ready"
        self._prompt_box.setEnabled(ready)
        self._send_button.setEnabled(ready)
        if ready and self._pending_availability == "AVAILABLE":
            self._logger.info("Autorun availability released after send enabled")
            self._pending_availability = None
            self._emit_availability("AVAILABLE")

    def _on_chat_availability(self, state: str) -> None:
        self._last_availability = state
        if state == "AVAILABLE" and not self._send_button.isEnabled():
            self._pending_availability = state
            self._logger.info("Availability buffered until send is enabled")
            return
        self._pending_availability = None
        self._emit_availability(state)

    def _emit_availability(self, state: str) -> None:
        for callback in list(self._availability_callbacks):
            try:
                callback(state)
            except Exception:
                continue

    def register_availability_callback(self, callback: Callable[[str], None]) -> bool:
        if self._chat_server is None:
            self._logger.warning("Availability callback registration failed: chat server not initialized")
            return False
        self._availability_callbacks.append(callback)
        if not self._availability_hooked:
            self._chat_server.register_availability_callback(self._on_chat_availability)
            self._availability_hooked = True
        if self._last_availability == "AVAILABLE" and not self._send_button.isEnabled():
            self._pending_availability = "AVAILABLE"
        elif self._last_availability:
            try:
                callback(self._last_availability)
            except Exception:
                pass
        return True

    def autorun_stage_message(self, text: str, image_paths: Iterable[Path]) -> None:
        paths = list(image_paths)
        self._logger.info(
            "Autorun staging message: chars=%d images=%d",
            len(text),
            len(paths),
        )
        self._prompt_box.setPlainText(text)
        self._attachments_bar.clear()
        if paths:
            self._attachments_bar.add_images(paths)
        self._prompt_box.setFocus()
        cursor = self._prompt_box.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        self._prompt_box.setTextCursor(cursor)

    def autorun_submit_message(self) -> None:
        if not self._send_button.isEnabled():
            self._logger.warning("Autorun submit blocked: Send button disabled")
            return
        self._logger.info("Autorun submitting message via Send button")
        self._send_button.click()

    def get_last_assistant_message(self) -> str:
        if self._chat_server is None:
            return ""
        return self._chat_server.get_last_assistant_message()

    def _on_send_clicked(self) -> None:
        text = self._prompt_box.toPlainText().strip()
        if not text:
            return
        attachments = self._attachments_bar.get_paths()

        self._add_message(create_message_widget(MessageType.USER, text, attachments=attachments))
        self._add_tools_advertisement()
        receive_widget = create_message_widget(MessageType.ASSISTANT, "")
        receive_widget.start_stream_buffering()
        self._current_receive = receive_widget
        self._current_receive_pending = True
        self._add_message(receive_widget)

        self._prompt_box.clear()
        self._attachments_bar.clear()

        if self._chat_server is None:
            self._logger.warning("Chat server not initialized")
            return
        self._chat_server.send_message(text, image_paths=attachments)

    def _on_stream_chunk(self, chunk: str) -> None:
        self.stream_chunk_received.emit(chunk)

    def _on_stream_end(self) -> None:
        self.stream_completed.emit()

    def _on_tool_call_callback(self, tool_call: object) -> None:
        self.tool_call_received.emit(tool_call)

    def _on_tool_result_callback(self, tool_call: object, result: object) -> None:
        self.tool_result_received.emit(tool_call, result)

    def _on_followup_callback(self) -> None:
        self.followup_reply_started.emit()

    def _append_stream_chunk(self, chunk: str) -> None:
        if not self._current_receive:
            return
        if self._current_receive_pending:
            self._logger.info("Assistant received first chunk; clearing pending flag")
            self._current_receive_pending = False
        self._current_receive.append_text(chunk)
        self._maybe_scroll_to_bottom()

    def _finalize_stream_message(self) -> None:
        if not self._current_receive:
            return
        if self._current_receive_pending:
            return
        self._current_receive.flush_stream_log()

    def _on_tool_call(self, tool_call: object) -> None:
        name = getattr(tool_call, "name", "tool")
        args = getattr(tool_call, "arguments", {})
        if self._current_receive is not None:
            existing_text = self._current_receive.get_text()
            self._logger.info(
                "Tool call UI: assistant text length=%d pending=%s",
                len(existing_text),
                self._current_receive_pending,
            )
            if self._current_receive_pending:
                self._logger.info("Tool call UI: removing pending assistant bubble")
                self._remove_message(self._current_receive)
                self._current_receive = None
                self._current_receive_pending = False
        request = create_message_widget(MessageType.MCP_REQUEST, f"{name}")
        if isinstance(args, dict) and args:
            request.set_details([(key, json.dumps(value)) for key, value in args.items()])
            request.set_details_visible(True)
        self._add_message(request)
        if self._current_receive is not None:
            self._current_receive.set_details([("tool_call", name)])
            self._current_receive.set_details_visible(True)

    def _on_tool_result(self, tool_call: object, result: object) -> None:
        name = getattr(tool_call, "name", "tool")
        response = create_message_widget(MessageType.MCP_RESPONSE, f"{name} result")
        if isinstance(result, dict) and result:
            response.set_details([(key, json.dumps(value)) for key, value in result.items()])
            response.set_details_visible(True)
        self._add_message(response)

    def _on_followup_reply_started(self) -> None:
        receive_widget = create_message_widget(MessageType.ASSISTANT, "")
        receive_widget.start_stream_buffering()
        self._current_receive = receive_widget
        self._current_receive_pending = True
        self._add_message(receive_widget)

    def _add_tools_advertisement(self) -> None:
        if self._chat_server is None:
            return
        payload = self._chat_server.get_tools_advertisement()
        if not payload:
            return
        content, details = payload
        bubble = create_message_widget(MessageType.TOOLS_ADVERTISEMENT, content)
        if details:
            bubble.set_details(details)
            bubble.set_details_visible(True)
        self._add_message(bubble)

    def _on_auto_scroll_toggled(self, checked: bool) -> None:
        if checked:
            self._maybe_scroll_to_bottom()

    def _maybe_scroll_to_bottom(self) -> None:
        if not self._auto_scroll_toggle.isChecked():
            return
        bar = self._history_scroll.verticalScrollBar()
        bar.setValue(bar.maximum())


class ChatInputBox(QtWidgets.QTextEdit):
    sendRequested = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(48)
        self.setMaximumHeight(108)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Minimum,
        )
        self.document().contentsChanged.connect(self._update_height)
        self._update_height()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
            modifiers = event.modifiers()
            if modifiers & (QtCore.Qt.KeyboardModifier.ShiftModifier | QtCore.Qt.KeyboardModifier.ControlModifier):
                super().keyPressEvent(event)
                return
            event.accept()
            self.sendRequested.emit()
            return
        super().keyPressEvent(event)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self.document().setTextWidth(self.viewport().width())
        self._update_height()

    def _update_height(self) -> None:
        self.document().setTextWidth(self.viewport().width())
        doc_height = self.document().documentLayout().documentSize().height()
        margins = self.contentsMargins()
        frame = self.frameWidth()
        target = int(doc_height + margins.top() + margins.bottom() + 2 * frame + 6)
        min_h = self.minimumHeight()
        max_h = self.maximumHeight()
        clamped = max(min_h, min(target, max_h))
        self.setFixedHeight(clamped)
        if target > max_h:
            self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        else:
            self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)



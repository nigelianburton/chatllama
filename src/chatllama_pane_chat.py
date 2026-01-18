import logging
from typing import Optional
from PyQt6 import QtCore, QtGui, QtWidgets
import markdown
from message_bubble import (
    MessageBubble, 
    UserInstructionContent, 
    UserInstructionWithAttachmentsContent,
    ToolRequestContent,
    ToolResponseContent,
    AssistantContent
)

logger = logging.getLogger(__name__)


# MessageBubble moved to message_bubble.py


class PromptInput(QtWidgets.QTextEdit):
    """Custom QTextEdit that sends on Enter (unless Ctrl is held)."""
    send_requested = QtCore.pyqtSignal()
    images_dropped = QtCore.pyqtSignal(list)  # Emits list of image file paths
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
    
    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """Handle key press: Enter sends, Ctrl+Enter adds newline."""
        if event.key() == QtCore.Qt.Key.Key_Return or event.key() == QtCore.Qt.Key.Key_Enter:
            if event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier:
                # Ctrl+Enter: add newline
                super().keyPressEvent(event)
            else:
                # Enter alone: send message
                self.send_requested.emit()
        else:
            super().keyPressEvent(event)

    def _mime_has_images(self, mime: QtCore.QMimeData) -> bool:
        if mime.hasUrls():
            for url in mime.urls():
                path = url.toLocalFile()
                if path:
                    ext = path.split('.')[-1].lower()
                    if ext in {"png", "jpg", "jpeg", "bmp", "gif", "webp"}:
                        return True
        return False

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:
        if self._mime_has_images(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QtGui.QDragMoveEvent) -> None:
        if self._mime_has_images(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        mime = event.mimeData()
        paths: list[str] = []
        if mime.hasUrls():
            for url in mime.urls():
                path = url.toLocalFile()
                if path:
                    ext = path.split('.')[-1].lower()
                    if ext in {"png", "jpg", "jpeg", "bmp", "gif", "webp"}:
                        paths.append(path)
        if paths:
            event.acceptProposedAction()
            self.images_dropped.emit(paths)
        else:
            event.ignore()


class ChatPanel(QtWidgets.QWidget):
    """Chat panel widget with history and input."""
    send_requested = QtCore.pyqtSignal(str)  # Emits message text
    
    def __init__(self, parent=None):
        super().__init__(parent)
        logger.info(f"[ChatPanel __init__] START - self={id(self)}")
        self.setObjectName("ChatPanel")
        
        # Initialize attributes to None (will be set in _build_ui)
        self.history_widget: Optional[QtWidgets.QListWidget] = None
        self.prompt_input: Optional[PromptInput] = None
        self.send_btn: Optional[QtWidgets.QPushButton] = None
        self.attachments_container: Optional[QtWidgets.QFrame] = None
        self.attachments_layout: Optional[QtWidgets.QHBoxLayout] = None
        self.input_row: Optional[QtWidgets.QHBoxLayout] = None
        self._attachments: list[str] = []  # File paths of attached images (max 3)
        
        # List to track all message widgets (tuples of (MessageBubble, QListWidgetItem))
        self.message_widgets: list[tuple[MessageBubble, QtWidgets.QListWidgetItem]] = []
        # Streaming state: current assistant bubble + item for live updates
        self._current_stream_bubble: Optional[MessageBubble] = None
        self._current_stream_item: Optional[QtWidgets.QListWidgetItem] = None
        
        logger.info(f"[ChatPanel __init__] About to call _build_ui(), self={id(self)}")
        self._build_ui()
        logger.info(f"[ChatPanel __init__] END - self={id(self)}, history_widget={id(self.history_widget) if self.history_widget else 'None'}")
    
    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # History panel - use QListWidget to display message bubbles
        self.history_widget = QtWidgets.QListWidget()
        logger.info(f"[ChatPanel Init] Created history_widget: widget={self.history_widget}, id={id(self.history_widget)}, self={id(self)}")
        self.history_widget.setSpacing(5)  # 5px spacing between items
        self.history_widget.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.history_widget.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                border-radius: 0px;
                padding: 8px;
                margin: 0px;
            }
            QListWidget::item {
                background-color: transparent;
                border: none;
            }
        """)

        # Input row: prompt left, attachments panel on right
        self.input_row = QtWidgets.QHBoxLayout()
        self.input_row.setContentsMargins(8, 4, 8, 4)
        self.input_row.setSpacing(6)

        # Prompt input
        self.prompt_input = PromptInput()
        self.prompt_input.setPlaceholderText("Type your message here... (Enter to send, Ctrl+Enter for newline). Drag up to 3 images here.")
        self.prompt_input.setMaximumHeight(80)
        self.prompt_input.setStyleSheet(
            """
            QTextEdit {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 6px;
                margin: 0px;
            }
            """
        )
        self.prompt_input.send_requested.connect(self._on_send)
        self.prompt_input.images_dropped.connect(self._on_images_dropped)
        logger.info(f"ChatPanel signals connected. Container exists: {self.attachments_container is not None}")

        # Ensure prompt expands while attachments take fixed width
        self.prompt_input.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.input_row.addWidget(self.prompt_input, 1)

        # Attachments container on the right
        self.attachments_container = QtWidgets.QFrame()
        self.attachments_container.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.attachments_container.setStyleSheet("background-color: #f5f5f5; border: 1px solid #cccccc; border-radius: 4px;")
        self.attachments_container.setMinimumHeight(80)
        self.attachments_container.setMaximumHeight(80)
        self.attachments_container.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        self.attachments_layout = QtWidgets.QHBoxLayout()
        self.attachments_layout.setContentsMargins(4, 4, 4, 4)
        self.attachments_layout.setSpacing(4)
        self.attachments_container.setLayout(self.attachments_layout)
        # Start hidden until attachments are present
        self.attachments_container.setVisible(False)
        self.input_row.addWidget(self.attachments_container)

        # Send button
        self.send_btn = QtWidgets.QPushButton("Send (Ctrl+Enter)")
        self.send_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #e0e0e0;
                color: #1a1a1a;
                border: 1px solid #b0b0b0;
                border-radius: 4px;
                padding: 6px 10px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #d5d5d5;
            }
            QPushButton:pressed {
                background-color: #c9c9c9;
            }
            """
        )
        self.send_btn.setMaximumHeight(32)
        self.send_btn.clicked.connect(self._on_send)

        # Add components directly to layout
        logger.info(f"[ChatPanel Init] Before addWidget - history_widget: {self.history_widget}")
        layout.addWidget(self.history_widget, 1)  # Takes remaining space
        logger.info(f"[ChatPanel Init] After addWidget - history_widget: {self.history_widget}")
        layout.addLayout(self.input_row)
        layout.addWidget(self.send_btn)

        logger.info(f"[ChatPanel Init] Before setLayout - history_widget: {self.history_widget}")
        self.setLayout(layout)
        logger.info(f"[ChatPanel Init] After setLayout - history_widget: {self.history_widget}")
    
    def _on_images_dropped(self, paths: list[str]) -> None:
        """Handle dropped images directly - add up to 3 thumbnails to the container."""
        logger.info(f"Images dropped: {len(paths)} file(s)")
        logger.info(f"_on_images_dropped: self={id(self)}, container={id(self.attachments_container) if self.attachments_container else 'None'}, layout={id(self.attachments_layout) if self.attachments_layout else 'None'}")
        
        # Validate container exists - check is not None explicitly
        if self.attachments_container is None or self.attachments_layout is None:
            logger.error(f"Attachments container not initialized! container={self.attachments_container}, layout={self.attachments_layout}")
            return
        
        # Clear existing thumbnails
        while self.attachments_layout.count() > 0:
            item = self.attachments_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Store paths (cap at 3)
        self._attachments = paths[:3]
        logger.info(f"Attachments stored: {len(self._attachments)} -> {self._attachments}")
        
        # Add new thumbnails directly
        for path in self._attachments:
            thumb = QtWidgets.QLabel()
            pixmap = QtGui.QPixmap(path)
            
            if pixmap.isNull():
                # Show error indicator if image can't be loaded
                thumb.setText("❌")
                thumb.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                thumb.setStyleSheet("background-color: #ffcccc; border: 1px solid #999; border-radius: 4px;")
                logger.warning(f"Failed to load image: {path}")
            else:
                # Scale to 64x64 maintaining aspect ratio
                scaled = pixmap.scaledToHeight(64, QtCore.Qt.TransformationMode.SmoothTransformation)
                thumb.setPixmap(scaled)
                thumb.setStyleSheet("border: 1px solid #666; border-radius: 4px;")
            
            thumb.setMaximumSize(64, 64)
            thumb.setMinimumSize(64, 64)
            self.attachments_layout.addWidget(thumb)
        
        # Calculate and set container width based on number of thumbnails
        count = len(self._attachments)
        if count > 0:
            thumb_size = 64
            # Width = (count * thumb_size) + ((count-1) * spacing) + (2 * margin)
            width = count * thumb_size + (count - 1) * 4 + 8
            self.attachments_container.setMinimumWidth(width)
            self.attachments_container.setMaximumWidth(width)
            self.attachments_container.setVisible(True)
            logger.debug(f"Attachments dropped: {count} thumbnail(s), width={width}")
        else:
            self.attachments_container.setVisible(False)

    def _update_attachments_view(self) -> None:
        """Refresh the attachments thumbnail strip from the _attachments list and adjust container width."""
        if self.attachments_container is None or self.attachments_layout is None:
            logger.debug("Attachments view update skipped: container or layout is None")
            return

        logger.debug(f"_update_attachments_view called with {len(self._attachments)} attachments")

        # Clear existing thumbnails
        while self.attachments_layout.count():
            item = self.attachments_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        # Add thumbnails for current attachments (up to 3)
        thumb_size = 64
        for idx, path in enumerate(self._attachments[:3]):
            label = QtWidgets.QLabel()
            label.setFixedSize(thumb_size, thumb_size)
            label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("border: 1px solid #888888; border-radius: 4px;")
            
            # Load and scale image
            logger.debug(f"Loading image {idx+1}: {path}")
            pix = QtGui.QPixmap(path)
            if not pix.isNull():
                logger.debug(f"Image {idx+1} loaded successfully, size: {pix.width()}x{pix.height()}")
                scaled_pix = pix.scaled(thumb_size, thumb_size, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
                label.setPixmap(scaled_pix)
            else:
                logger.debug(f"Image {idx+1} failed to load: {path}")
                label.setText("Image\nnot found")
                label.setStyleSheet("color: #ff0000; background-color: #dddddd; border: 1px solid #888888; border-radius: 4px;")
            
            self.attachments_layout.addWidget(label)
            logger.debug(f"Added thumbnail {idx+1} to layout")

        # Compute width based on number of attachments and set visibility
        count = len(self._attachments)
        if count > 0:
            # Width = (count * thumb_size) + ((count-1) * spacing) + (2 * margin)
            width = count * thumb_size + (count - 1) * 4 + 8
            self.attachments_container.setMinimumWidth(width)
            self.attachments_container.setMaximumWidth(width)
            self.attachments_container.setVisible(True)
            logger.debug(f"Attachments view: {count} thumbnail(s), width={width}, layout_count={self.attachments_layout.count()}, container_visible={self.attachments_container.isVisible()}")
        else:
            self.attachments_container.setMinimumWidth(0)
            self.attachments_container.setMaximumWidth(0)
            self.attachments_container.setVisible(False)
            logger.debug("Attachments view: no attachments, hiding container")

        # Force re-layout and repaint
        self.attachments_container.updateGeometry()
        self.attachments_container.repaint()
        if self.layout():
            self.layout().invalidate()
            self.updateGeometry()
            self.update()
        logger.debug("Attachments view update complete")


    def clear_attachments(self) -> None:
        """Clear all attachments and hide the container."""
        self._attachments.clear()
        self._update_attachments_view()

    def get_attachments(self) -> list[str]:
        """Return current attachment file paths (up to 3)."""
        return list(self._attachments)
    
    def _on_send(self) -> None:
        """Emit signal when send is requested."""
        if self.prompt_input:
            text = self.prompt_input.toPlainText().strip()
            if text:
                self.send_requested.emit(text)
    
    def _create_message_bubble(self, text: str, message_type: str = "system", 
                              image_path: Optional[str] = None,
                              image_paths: Optional[list[str]] = None,
                              tool_request: Optional[dict] = None,
                              tool_response: Optional[dict] = None) -> tuple[MessageBubble, QtWidgets.QListWidgetItem]:
        """Create a message bubble with appropriate content widget.
        
        Args:
            text: The text to display
            message_type: Type of message - "user", "assistant", "system", "tool", "error", etc.
            image_path: Optional path to single image (for backward compatibility)
            image_paths: Optional list of image paths
            tool_request: Optional dict with tool request data (name, arguments)
            tool_response: Optional dict with tool response data (name, result)
            
        Returns:
            Tuple of (MessageBubble widget, QListWidgetItem)
        """
        if self.history_widget is None:
            raise RuntimeError(f"History widget is None! Type: {type(self.history_widget)}")
        
        # Log bubble creation details
        bubble_features = []
        if image_path or image_paths:
            bubble_features.append("with_images")
        if tool_request:
            bubble_features.append(f"tool_request")
        if tool_response:
            tool_name = tool_response.get("name", "unknown")
            bubble_features.append(f"tool_response:{tool_name}")
        
        features_str = f" [{', '.join(bubble_features)}]" if bubble_features else ""
        text_preview = text[:50] + "..." if len(text) > 50 else text
        logger.info(f"[Bubble Creation] Adding {message_type.upper()} bubble to history{features_str} - Text: \"{text_preview}\"")
        
        # Create appropriate content widget based on message type
        content_widget = None
        
        if message_type == "user":
            # Check if user message has attachments
            if image_paths:
                content_widget = UserInstructionWithAttachmentsContent(text, image_paths)
            elif image_path:
                content_widget = UserInstructionWithAttachmentsContent(text, [image_path])
            else:
                content_widget = UserInstructionContent(text)
        
        elif message_type == "assistant":
            content_widget = AssistantContent(text)
        
        elif tool_request:
            tool_name = tool_request.get("name", "Unknown Tool")
            arguments = tool_request.get("arguments", {})
            content_widget = ToolRequestContent(tool_name, arguments)
        
        elif tool_response:
            tool_name = tool_response.get("name", "Unknown")
            response_data = tool_response.get("result", {})
            content_widget = ToolResponseContent(tool_name, response_data)
        
        else:
            # Default: plain text
            content_widget = UserInstructionContent(text)
        
        # Create the bubble with the content widget
        bubble = MessageBubble(msg_type=message_type, content_widget=content_widget)
        bubble.show()
        
        # Create list item
        item = QtWidgets.QListWidgetItem(self.history_widget)
        size_hint = bubble.sizeHint()
        item.setSizeHint(size_hint)
        
        # Add to list widget
        self.history_widget.addItem(item)
        self.history_widget.setItemWidget(item, bubble)
        
        # Track in message widgets list
        self.message_widgets.append((bubble, item))
        
        # If assistant bubble started for streaming, remember references
        if message_type == "assistant" and (text is None or text == ""):
            self._current_stream_bubble = bubble
            self._current_stream_item = item
        
        logger.info(f"[Bubble Creation] Successfully added bubble #{len(self.message_widgets)} to history (size: {size_hint.width()}×{size_hint.height()}px)")
        logger.debug(f"Total message widgets: {len(self.message_widgets)}")
        
        return (bubble, item)
    
    def append_to_history(self, text: str, append_only: bool = False, message_type: str = "system", tool_response: Optional[dict] = None) -> None:
        """Append text to history widget as a message bubble.
        
        Args:
            text: The text to append
            append_only: Ignored for QListWidget (always creates a new bubble)
            message_type: Type of message - "user", "assistant", "system", "tool", "error", "thinking", "tool_request", "tool_response"
            tool_response: Optional dict with tool response data (name, arguments, result)
        """
        logger.info(f"[ChatPanel Append] Called with message_type={message_type}, self={id(self)}, history_widget={self.history_widget}")
        if self.history_widget is None:
            logger.warning("History widget is None!")
            return
        # Streaming updates for assistant: append to existing bubble
        if append_only and message_type == "assistant":
            # Initialize streaming bubble if not present
            if self._current_stream_bubble is None:
                bubble, item = self._create_message_bubble("", "assistant")
                self._current_stream_bubble = bubble
                self._current_stream_item = item
            # Append chunk
            if self._current_stream_bubble is not None:
                self._current_stream_bubble.append_stream_text(text)
                # Update item size to fit content
                if self._current_stream_item is not None:
                    self._current_stream_item.setSizeHint(self._current_stream_bubble.sizeHint())
            # Scroll to bottom
            self.history_widget.scrollToBottom()
            return

        # Non-streaming path: create a new bubble
        self._create_message_bubble(text, message_type, tool_response=tool_response)
        
        # Scroll to bottom
        self.history_widget.scrollToBottom()
    
    def clear_input(self) -> None:
        """Clear the prompt input field."""
        if self.prompt_input:
            self.prompt_input.clear()

    def finalize_streaming_assistant(self, text: str) -> None:
        """Finalize the current streaming assistant bubble with full content.

        Replaces the existing text with markdown-rendered HTML.
        """
        if self._current_stream_bubble is None:
            # No streaming bubble; create one normally
            self._create_message_bubble(text, "assistant")
            return
        
        bubble = self._current_stream_bubble
        
        # Find the AssistantContent widget inside the bubble
        frame_layout = bubble.rounded_frame.layout()
        if frame_layout and frame_layout.count() > 0:
            content_widget = frame_layout.itemAt(0).widget()
            if isinstance(content_widget, AssistantContent):
                content_widget.set_text(text)
        
        # Update item size
        if self._current_stream_item is not None:
            self._current_stream_item.setSizeHint(bubble.sizeHint())
        
        # Clear streaming state
        self._current_stream_bubble = None
        self._current_stream_item = None
    
    def convert_assistant_to_tool_request(self, tool_name: str, arguments: dict) -> None:
        """Convert the current streaming assistant bubble to a tool_request bubble.
        
        This is called when a tool request is detected in the model output.
        The existing assistant bubble is updated with tool request content.
        """
        if self._current_stream_bubble is None:
            logger.warning("No current stream bubble to convert")
            return
        
        bubble = self._current_stream_bubble
        
        # Update bubble message type
        bubble.msg_type = "tool_request"
        bubble.display_type = "tool_request"
        
        # Create and set new content widget
        content_widget = ToolRequestContent(tool_name, arguments)
        bubble.set_content_widget(content_widget)
        
        # Update frame style to tool_request color
        from message_bubble import MESSAGE_COLORS
        bg_color = MESSAGE_COLORS.get("tool_request", MESSAGE_COLORS["system"])
        bubble._update_frame_style(bg_color)
        
        # Update type overlay
        bubble.type_overlay.setText("TOOL_REQUEST")
        
        # Update item size
        if self._current_stream_item is not None:
            self._current_stream_item.setSizeHint(bubble.sizeHint())
        
        logger.info(f"[Bubble Conversion] Converted assistant bubble to tool_request: {tool_name}")
    
    def get_history_text(self) -> str:
        """Get all text from history widget (plain text)."""
        if self.history_widget:
            texts = []
            for i in range(self.history_widget.count()):
                item = self.history_widget.item(i)
                widget = self.history_widget.itemWidget(item)
                if isinstance(widget, MessageBubble):
                    texts.append(widget.toPlainText() if hasattr(widget, 'toPlainText') else str(widget))
            return "\n".join(texts)
        return ""
    
    def set_input_text(self, text: str) -> None:
        """Set text in the input field."""
        if self.prompt_input:
            self.prompt_input.setPlainText(text)

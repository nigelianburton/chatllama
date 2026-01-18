import logging
from typing import Optional
from PyQt6 import QtCore, QtGui, QtWidgets

logger = logging.getLogger(__name__)


class PromptInput(QtWidgets.QTextEdit):
    """Custom QTextEdit that sends on Enter (unless Ctrl is held)."""
    send_requested = QtCore.pyqtSignal()
    
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


class ChatPanel(QtWidgets.QWidget):
    """Chat panel widget with history and input."""
    send_requested = QtCore.pyqtSignal(str)  # Emits message text
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ChatPanel")
        
        self.history_widget: Optional[QtWidgets.QTextEdit] = None
        self.prompt_input: Optional[PromptInput] = None
        self.send_btn: Optional[QtWidgets.QPushButton] = None
        
        self._build_ui()
    
    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        chat_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        chat_splitter.setHandleWidth(2)

        # Use QTextEdit instead of QPlainTextEdit to support HTML/rich text
        self.history_widget = QtWidgets.QTextEdit()
        self.history_widget.setReadOnly(True)
        self.history_widget.setPlaceholderText("Chat history will appear here...")
        # Set stylesheet for better appearance
        self.history_widget.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
            }
        """)

        self.prompt_input = PromptInput()
        self.prompt_input.setPlaceholderText("Type your message here... (Enter to send, Ctrl+Enter for newline)")
        self.prompt_input.send_requested.connect(self._on_send)

        # Send button
        self.send_btn = QtWidgets.QPushButton("Send")
        self.send_btn.clicked.connect(self._on_send)
        self.prompt_input.setMaximumHeight(120)

        # Bottom panel for prompt + send button
        prompt_panel = QtWidgets.QWidget()
        prompt_layout = QtWidgets.QVBoxLayout()
        prompt_layout.setContentsMargins(0, 0, 0, 0)
        prompt_layout.setSpacing(6)
        prompt_layout.addWidget(self.prompt_input)
        prompt_layout.addWidget(self.send_btn)
        prompt_panel.setLayout(prompt_layout)

        chat_splitter.addWidget(self.history_widget)
        chat_splitter.addWidget(prompt_panel)
        chat_splitter.setSizes([700, 300])

        layout.addWidget(QtWidgets.QLabel("Chat"))
        layout.addWidget(chat_splitter, 1)
        self.setLayout(layout)
    
    def _on_send(self) -> None:
        """Emit signal when send is requested."""
        if self.prompt_input:
            text = self.prompt_input.toPlainText().strip()
            if text:
                self.send_requested.emit(text)
    
    def append_to_history(self, text: str, append_only: bool = False, message_type: str = "system") -> None:
        """Append text to history widget with optional styling.
        
        Args:
            text: The text to append
            append_only: If True, append without adding newlines. If False, add as new message block
            message_type: Type of message - "user", "assistant", "system", "tool", "error"
        """
        if not self.history_widget:
            return
        
        # Map message types to colors and styles
        styles = {
            "user": {
                "bg_color": "#e3f2fd",  # Light blue
                "border_color": "#2196f3",  # Blue
                "text_color": "#0d47a1",  # Dark blue
                "label": "You"
            },
            "assistant": {
                "bg_color": "#f3e5f5",  # Light purple
                "border_color": "#9c27b0",  # Purple
                "text_color": "#4a148c",  # Dark purple
                "label": "Assistant"
            },
            "system": {
                "bg_color": "#fff3e0",  # Light orange
                "border_color": "#ff9800",  # Orange
                "text_color": "#e65100",  # Dark orange
                "label": "System"
            },
            "tool": {
                "bg_color": "#e8f5e9",  # Light green
                "border_color": "#4caf50",  # Green
                "text_color": "#1b5e20",  # Dark green
                "label": "Tool"
            },
            "error": {
                "bg_color": "#ffebee",  # Light red
                "border_color": "#f44336",  # Red
                "text_color": "#b71c1c",  # Dark red
                "label": "Error"
            }
        }
        
        style = styles.get(message_type, styles["system"])
        
        if append_only:
            # For streaming chunks, just append plain text
            cursor = self.history_widget.textCursor()
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
            self.history_widget.setTextCursor(cursor)
            self.history_widget.insertPlainText(text)
        else:
            # For complete messages, wrap in styled box
            cursor = self.history_widget.textCursor()
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
            self.history_widget.setTextCursor(cursor)
            
            # Create HTML styled message box
            html = f"""
            <div style="margin: 8px 0; padding: 12px; background-color: {style['bg_color']}; 
                        border-left: 4px solid {style['border_color']}; border-radius: 4px;">
                <div style="font-weight: bold; color: {style['border_color']}; margin-bottom: 4px;">
                    {style['label']}
                </div>
                <div style="color: {style['text_color']}; white-space: pre-wrap; word-wrap: break-word;">
                    {text.replace('<', '&lt;').replace('>', '&gt;')}
                </div>
            </div>
            """
            self.history_widget.insertHtml(html)
        
        # Scroll to bottom
        self.history_widget.moveCursor(QtGui.QTextCursor.MoveOperation.End)
    
    def clear_input(self) -> None:
        """Clear the prompt input field."""
        if self.prompt_input:
            self.prompt_input.clear()
    
    def get_history_text(self) -> str:
        """Get all text from history widget (plain text)."""
        if self.history_widget:
            return self.history_widget.toPlainText()
        return ""
    
    def set_input_text(self, text: str) -> None:
        """Set text in the input field."""
        if self.prompt_input:
            self.prompt_input.setPlainText(text)

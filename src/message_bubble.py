"""Message bubble rendering using SVG for deterministic sizing and LLM control.

Each bubble type (instruction, reply, tool_request, etc.) generates an SVG string
with exact dimensions. MessageBubble renders the SVG using QSvgWidget.
"""

import logging
from typing import Optional
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtSvgWidgets import QSvgWidget

logger = logging.getLogger(__name__)

# Color scheme for different message types
MESSAGE_COLORS = {
    "instruction": "#e3f2fd",      # Light blue
    "reply": "#f3e5f5",            # Light purple
    "thinking": "#fff3e0",         # Light orange
    "tool_request": "#e8f5e9",     # Light green
    "tool_response": "#fce4ec",    # Light pink
    "system": "#f5f5f5",           # Light gray
    "user": "#e3f2fd",             # Light blue (same as instruction)
    "assistant": "#f3e5f5",         # Light purple (same as reply)
    "tool": "#e8f5e9",             # Light green (same as tool_request)
    "error": "#ffebee",            # Light red
}

# SVG text rendering parameters
BUBBLE_PADDING = 12  # 6px on each side
BUBBLE_WIDTH = 380
TEXT_FONT_SIZE = 11
BORDER_COLOR = "#888888"
BORDER_WIDTH = 1
BORDER_RADIUS = 8
OVERLAY_FONT_SIZE = 9


def _wrap_text(text: str, max_chars: int = 60) -> list[str]:
    """Wrap text into lines."""
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        if len(' '.join(current_line)) > max_chars:
            if len(current_line) > 1:
                current_line.pop()
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                lines.append(word)
                current_line = []
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines


def _calculate_text_height(text: str, max_chars: int = 60) -> int:
    """Calculate text height based on wrapped lines."""
    lines = _wrap_text(text, max_chars)
    line_height = 16  # approximate line height in pixels
    return len(lines) * line_height


def generate_instruction_svg(text: str, msg_type: str = "instruction", overlay_text: str = "INSTRUCTION") -> tuple[str, int]:
    """Generate SVG for instruction/reply text bubble.
    
    Returns (svg_string, height)
    """
    bg_color = MESSAGE_COLORS.get(msg_type, MESSAGE_COLORS["system"])
    
    # Calculate dimensions
    text_height = _calculate_text_height(text)
    content_height = text_height + BUBBLE_PADDING
    total_height = content_height
    
    # Build SVG
    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{BUBBLE_WIDTH}" height="{total_height}">',
        f'  <!-- Background with rounded corners -->',
        f'  <rect x="0" y="0" width="{BUBBLE_WIDTH}" height="{total_height}" rx="{BORDER_RADIUS}" ry="{BORDER_RADIUS}"',
        f'        fill="{bg_color}" stroke="{BORDER_COLOR}" stroke-width="{BORDER_WIDTH}"/>',
        f'  <!-- Text content -->',
    ]
    
    # Add wrapped text lines
    y_pos = 6 + BUBBLE_PADDING // 2
    for line in _wrap_text(text):
        svg_lines.append(
            f'  <text x="6" y="{y_pos}" font-family="Arial, sans-serif" font-size="{TEXT_FONT_SIZE}" fill="#000000">'
            f'{_escape_xml(line)}</text>'
        )
        y_pos += 16
    
    svg_lines.append('</svg>')
    
    svg_string = '\n'.join(svg_lines)
    return svg_string, total_height


def generate_tool_request_svg(tool_name: str, arguments: dict) -> tuple[str, int]:
    """Generate SVG for tool request bubble."""
    bg_color = MESSAGE_COLORS["tool_request"]
    
    # Calculate height based on tool name and arguments
    lines = [f"Tool: {tool_name}"]
    if arguments:
        lines.append("Arguments:")
        for key, value in arguments.items():
            lines.append(f"  {key}: {str(value)[:40]}")
    
    text_height = len(lines) * 16
    content_height = text_height + BUBBLE_PADDING
    total_height = content_height
    
    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{BUBBLE_WIDTH}" height="{total_height}">',
        f'  <rect x="0" y="0" width="{BUBBLE_WIDTH}" height="{total_height}" rx="{BORDER_RADIUS}" ry="{BORDER_RADIUS}"',
        f'        fill="{bg_color}" stroke="{BORDER_COLOR}" stroke-width="{BORDER_WIDTH}"/>',
    ]
    
    y_pos = 6 + BUBBLE_PADDING // 2
    for i, line in enumerate(lines):
        weight = "bold" if i == 0 else "normal"
        size = 12 if i == 0 else TEXT_FONT_SIZE
        svg_lines.append(
            f'  <text x="6" y="{y_pos}" font-family="Arial, sans-serif" font-size="{size}" font-weight="{weight}" fill="#000000">'
            f'{_escape_xml(line)}</text>'
        )
        y_pos += 16
    
    svg_lines.append('</svg>')
    return '\n'.join(svg_lines), total_height


def generate_tool_response_svg(tool_name: str, response_data: dict) -> tuple[str, int]:
    """Generate SVG for tool response bubble."""
    bg_color = MESSAGE_COLORS["tool_response"]
    
    # Convert response to lines
    import json
    if isinstance(response_data, dict):
        response_text = json.dumps(response_data, indent=2)
    else:
        response_text = str(response_data)
    
    lines = response_text.split('\n')[:10]  # Limit to 10 lines for display
    text_height = len(lines) * 14
    content_height = text_height + BUBBLE_PADDING
    total_height = content_height
    
    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{BUBBLE_WIDTH}" height="{total_height}">',
        f'  <rect x="0" y="0" width="{BUBBLE_WIDTH}" height="{total_height}" rx="{BORDER_RADIUS}" ry="{BORDER_RADIUS}"',
        f'        fill="{bg_color}" stroke="{BORDER_COLOR}" stroke-width="{BORDER_WIDTH}"/>',
    ]
    
    y_pos = 6 + BUBBLE_PADDING // 2
    for line in lines:
        svg_lines.append(
            f'  <text x="6" y="{y_pos}" font-family="Courier, monospace" font-size="9" fill="#000000">'
            f'{_escape_xml(line[:50])}</text>'
        )
        y_pos += 14
    
    svg_lines.append('</svg>')
    return '\n'.join(svg_lines), total_height


def _escape_xml(text: str) -> str:
    """Escape XML special characters."""
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&apos;'))


class MessageBubble(QtWidgets.QFrame):
    """Message bubble using SVG rendering for deterministic sizing.
    
    Architecture:
    - Content stored as SVG string
    - QSvgWidget renders the SVG
    - sizeHint() returns exact dimensions from SVG
    - Streaming updates SVG and re-renders
    """
    
    def __init__(self, msg_type: str = "system", content_widget: Optional[QtWidgets.QWidget] = None, parent=None):
        super().__init__(parent)
        self.msg_type = msg_type
        self.is_selected = False
        self.current_text = ""
        self.current_height = 40  # Min height
        self.attachments_container: Optional[QtWidgets.QFrame] = None
        self.attachments_layout: Optional[QtWidgets.QHBoxLayout] = None
        
        # Normalize message type
        type_map = {
            "instruction": "instruction",
            "user": "instruction",
            "reply": "reply",
            "assistant": "reply",
            "thinking": "thinking",
            "tool_request": "tool_request",
            "tool": "tool_request",
            "tool_response": "tool_response",
            "system": "system",
            "error": "error",
        }
        self.display_type = type_map.get(msg_type.lower(), "system")
        
        # Set bubble size policy
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        
        # Root layout - 12px top padding to separate bubble from parent edge
        root_layout = QtWidgets.QVBoxLayout()
        root_layout.setContentsMargins(0, 12, 0, 0)  # 12px top padding for overlay space
        root_layout.setSpacing(0)
        self.setLayout(root_layout)
        
        # SVG widget for rendering
        self.svg_widget = QSvgWidget()
        self.svg_widget.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        root_layout.addWidget(self.svg_widget)

        # Optional thumbnail strip for attached images
        self.attachments_container = QtWidgets.QFrame()
        self.attachments_container.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed
        )
        self.attachments_layout = QtWidgets.QHBoxLayout()
        self.attachments_layout.setContentsMargins(6, 4, 6, 6)
        self.attachments_layout.setSpacing(6)
        self.attachments_container.setLayout(self.attachments_layout)
        self.attachments_container.setVisible(False)
        self.attachments_container.setMinimumWidth(0)
        self.attachments_container.setMaximumWidth(BUBBLE_WIDTH)
        root_layout.addWidget(self.attachments_container)
        
        # Type overlay label (positioned absolutely at top-left, flush with parent top)
        self.type_overlay = QtWidgets.QLabel(self)
        self.type_overlay.setText(self.display_type.upper())
        self.type_overlay.setStyleSheet(
            "color: #333333; font-size: 8px; font-weight: bold; background-color: #FFFF00; padding: 1px 3px;"
        )
        self.type_overlay.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft)
        self.type_overlay.adjustSize()
        self.type_overlay.move(2, 0)  # Flush with top of parent
        self.type_overlay.raise_()
        
        # Set initial content if provided
        if content_widget:
            self.set_content_widget(content_widget)

    def set_images(self, image_paths: list[str]) -> None:
        """Display up to 3 image thumbnails beneath the text bubble."""
        if self.attachments_container is None or self.attachments_layout is None:
            logger.debug("Attachments container not initialized on MessageBubble")
            return

        # Clear previous thumbnails
        while self.attachments_layout.count():
            item = self.attachments_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        paths = list(image_paths or [])[:3]
        if not paths:
            self.attachments_container.setVisible(False)
            self.attachments_container.setMinimumHeight(0)
            self.attachments_container.setMaximumHeight(0)
            self.updateGeometry()
            return

        thumb_size = 72
        for path in paths:
            label = QtWidgets.QLabel()
            label.setFixedSize(thumb_size, thumb_size)
            label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("border: 1px solid #666; border-radius: 4px; background-color: #ffffff;")

            pix = QtGui.QPixmap(path)
            if not pix.isNull():
                scaled = pix.scaled(
                    thumb_size,
                    thumb_size,
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    QtCore.Qt.TransformationMode.SmoothTransformation,
                )
                label.setPixmap(scaled)
            else:
                label.setText("Image\nnot found")
                label.setStyleSheet("color: #ff0000; background-color: #f5f5f5; border: 1px solid #666; border-radius: 4px;")

            self.attachments_layout.addWidget(label)

        # Adjust container sizing and visibility
        width = len(paths) * thumb_size + max(0, len(paths) - 1) * self.attachments_layout.spacing() + 12
        self.attachments_container.setMinimumWidth(width)
        self.attachments_container.setMaximumWidth(max(width, BUBBLE_WIDTH))
        self.attachments_container.setMinimumHeight(thumb_size + 12)
        self.attachments_container.setMaximumHeight(thumb_size + 12)
        self.attachments_container.setVisible(True)
        self.updateGeometry()
        self.update()
    
    def set_content_widget(self, content_widget: QtWidgets.QWidget) -> None:
        """Set content from a widget (for backwards compatibility).
        
        This converts the widget to SVG and renders it.
        """
        # Extract text from content widget if possible
        if hasattr(content_widget, 'text'):
            text = content_widget.text()
        else:
            text = "Content"
        
        self.current_text = text
        svg_str, height = generate_instruction_svg(text, self.display_type, self.display_type.upper())
        self.current_height = max(40, height)
        self._render_svg(svg_str)
    
    def set_text(self, text: str) -> None:
        """Set text content and render as SVG."""
        self.current_text = text
        svg_str, height = generate_instruction_svg(text, self.display_type, self.display_type.upper())
        self.current_height = max(40, height)
        self._render_svg(svg_str)
        # Update overlay text
        self.type_overlay.setText(self.display_type.upper())
        self.type_overlay.adjustSize()
    
    def append_stream_text(self, chunk: str) -> None:
        """Append chunk to text and re-render SVG."""
        self.current_text += chunk
        svg_str, height = generate_instruction_svg(self.current_text, self.display_type, self.display_type.upper())
        self.current_height = max(40, height)
        self._render_svg(svg_str)
    
    def _render_svg(self, svg_string: str) -> None:
        """Render SVG string in the widget."""
        try:
            svg_bytes = svg_string.encode('utf-8')
            self.svg_widget.load(QtCore.QByteArray(svg_bytes))
            self.update()
        except Exception as e:
            logger.error(f"Failed to render SVG: {e}")
    
    def set_selected(self, selected: bool) -> None:
        """Set selection state (for future use with red border)."""
        self.is_selected = selected
        # Could re-render with red border if needed
    
    def sizeHint(self) -> QtCore.QSize:
        """Return size based on SVG dimensions plus 12px top padding."""
        height = self.current_height + 12
        if self.attachments_container and self.attachments_container.isVisible():
            # Add attachments strip height plus small gap
            height += self.attachments_container.sizeHint().height() + 4
        return QtCore.QSize(BUBBLE_WIDTH, height)

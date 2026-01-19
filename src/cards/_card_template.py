from typing import Any, Dict, List, Optional
from PyQt6 import QtWidgets, QtCore
import logging

logger = logging.getLogger(__name__)


class AspectRatioFrame(QtWidgets.QFrame):
    """Frame that maintains a fixed 4:3 aspect ratio based on available width."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.setLineWidth(0)
        # Make background transparent so browser shows through
        self.setStyleSheet("AspectRatioFrame { background-color: transparent; border: 2px solid #d0e7f9; }")

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        # For 4:3 ratio: height = width * (3 / 4)
        height = int(width * 3 / 4)
        logger.debug(f"[AspectRatioFrame] heightForWidth({width}) = {height}")
        return height
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        logger.info(f"[AspectRatioFrame] resizeEvent: new size = {event.size()}, old size = {event.oldSize()}")
        # Force height recalculation when width changes
        if event.size().width() != event.oldSize().width():
            new_height = self.heightForWidth(event.size().width())
            self.setFixedHeight(new_height)
            logger.info(f"[AspectRatioFrame] Width changed, updated height to {new_height}")


class CardBase(QtWidgets.QFrame):
    """Template card container that behaves MCP-like (name + functions metadata).

    - Maintains 4:3 aspect by adjusting height for the current width.
    - Exposes `name` and `functions` similar to an MCP tool list.
    - Provides `set_card_widget()` to attach a concrete card implementation.
    """

    name: str = "card_template"
    functions: List[Dict[str, Any]] = [
        {
            "name": "render",
            "description": "Render the card contents inside a 4x3 container.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        }
    ]

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._current_card: Optional[QtWidgets.QWidget] = None
        
        # Set minimum size to ensure card is visible
        self.setMinimumHeight(300)
        # Remove frame styling to let content show through
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.setLineWidth(0)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._aspect_frame = AspectRatioFrame(self)
        self._aspect_layout = QtWidgets.QVBoxLayout(self._aspect_frame)
        self._aspect_layout.setContentsMargins(0, 0, 0, 0)
        self._aspect_layout.setSpacing(0)

        layout.addWidget(self._aspect_frame)

    def available_functions(self) -> List[Dict[str, Any]]:
        """Return MCP-like function metadata."""
        return self.functions

    def set_card_widget(self, widget: QtWidgets.QWidget) -> None:
        """Attach a concrete card widget into the aspect-ratio container."""
        logger.info(f"[CardBase] set_card_widget called with: {widget.__class__.__name__}")
        if self._current_card:
            logger.info(f"[CardBase] Removing existing card: {self._current_card.__class__.__name__}")
            self._current_card.setParent(None)
            self._aspect_layout.removeWidget(self._current_card)
        self._current_card = widget
        self._aspect_layout.addWidget(widget)
        # Force widget to be visible and update geometry
        widget.show()
        self._aspect_frame.updateGeometry()
        self.updateGeometry()
        logger.info(f"[CardBase] Widget added to layout. Widget size: {widget.size()}, visible: {widget.isVisible()}")
        logger.info(f"[CardBase] AspectFrame size: {self._aspect_frame.size()}, children: {len(self._aspect_frame.children())}")

    def showEvent(self, event):
        super().showEvent(event)
        logger.info(f"[CardBase] showEvent: size = {self.size()}, visible = {self.isVisible()}")
        logger.info(f"[CardBase] AspectFrame size = {self._aspect_frame.size()}, visible = {self._aspect_frame.isVisible()}")
        if self._current_card:
            logger.info(f"[CardBase] Current card ({self._current_card.__class__.__name__}) size = {self._current_card.size()}, visible = {self._current_card.isVisible()}")
    
    def call(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """Placeholder for MCP-like call dispatch; override in subclasses."""
        raise NotImplementedError("Card does not implement call dispatch")

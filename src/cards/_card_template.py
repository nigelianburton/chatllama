from typing import Any, Dict, List, Optional
from PyQt6 import QtWidgets, QtCore


class AspectRatioFrame(QtWidgets.QFrame):
    """Frame that maintains a fixed 4:3 aspect ratio based on available width."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.setLineWidth(1)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        # For 4:3 ratio: height = width * (3 / 4)
        return int(width * 3 / 4)


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
        if self._current_card:
            self._current_card.setParent(None)
            self._aspect_layout.removeWidget(self._current_card)
        self._current_card = widget
        self._aspect_layout.addWidget(widget)

    def call(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """Placeholder for MCP-like call dispatch; override in subclasses."""
        raise NotImplementedError("Card does not implement call dispatch")

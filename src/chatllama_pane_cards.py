import logging
from PyQt6 import QtWidgets

logger = logging.getLogger(__name__)


class CardsPanel(QtWidgets.QWidget):
    """Cards panel widget for future features."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CardsPanel")
        self._build_ui()
    
    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(QtWidgets.QLabel("Cards"))
        layout.addStretch(1)
        self.setLayout(layout)

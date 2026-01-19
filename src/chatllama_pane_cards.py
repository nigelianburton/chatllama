import logging
from PyQt6 import QtCore, QtWidgets
from cards.card_chrome import CardChrome

logger = logging.getLogger(__name__)


class CardsPanel(QtWidgets.QWidget):
    """Cards panel widget displaying card templates with embedded browser."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CardsPanel")
        self._build_ui()
    
    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create vertical-only scroll area
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Create container widget for the scroll area
        scroll_container = QtWidgets.QWidget()
        scroll_layout = QtWidgets.QVBoxLayout(scroll_container)
        scroll_layout.setContentsMargins(8, 8, 8, 8)
        scroll_layout.setSpacing(12)

        # Instantiate CardChrome with the image file path
        logger.info("Creating CardChrome widget with local image")
        self._card_chrome = CardChrome(
            parent=scroll_container,
            start_url=r"T:\pic1.JPG"
        )
        logger.info(f"CardChrome created: size={self._card_chrome.size()}, minimumHeight={self._card_chrome.minimumHeight()}")
        scroll_layout.addWidget(self._card_chrome)
        scroll_layout.addStretch(1)

        scroll_area.setWidget(scroll_container)
        layout.addWidget(scroll_area)
        self.setLayout(layout)
        logger.info("CardsPanel UI built successfully")

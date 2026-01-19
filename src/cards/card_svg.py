from typing import Any, Dict, List, Optional
from PyQt6 import QtCore, QtWidgets, QtSvgWidgets
from ._card_template import CardBase
import logging
import base64
from pathlib import Path

logger = logging.getLogger(__name__)


class CardSVG(CardBase):
    """SVG display card for visual content using QtSvg (no WebEngine)."""

    name: str = "card_svg"
    functions: List[Dict[str, Any]] = [
        {
            "name": "open_url",
            "description": "Load the given content or file path into the SVG view.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "SVG markup or image file path",
                    }
                },
                "required": ["url"],
            },
        }
    ]

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, start_content: str = "") -> None:
        logger.info(f"[CardSVG] __init__ called with parent: {parent.__class__.__name__ if parent else None}")
        super().__init__(parent)
        logger.info(f"[CardSVG] After super().__init__, CardBase size: {self.size()}")
        
        self._view = QtSvgWidgets.QSvgWidget(self)
        logger.info(f"[CardSVG] Created QSvgWidget for SVG rendering")
        
        self._view.setSizePolicy(
            QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        )
        self._view.setStyleSheet("QSvgWidget { background-color: white; border: 1px solid #ccc; }")
        self._view.setMinimumHeight(200)
        self._view.resize(400, 300)
        logger.info(f"[CardSVG] QSvgWidget configured. Size: {self._view.size()}, minHeight: {self._view.minimumHeight()}")
        
        self.set_card_widget(self._view)
        logger.info(f"[CardSVG] After set_card_widget. View parent: {self._view.parent().__class__.__name__ if self._view.parent() else None}")
        
        # Load initial content if provided
        if start_content:
            self.load_svg_content(start_content)
        logger.info(f"[CardSVG] __init__ complete. Initial content loaded")

    def load_svg_content(self, content: str) -> None:
        """Load SVG content into the widget. Content can be SVG XML string or image file path."""
        if not content:
            return
        
        logger.info(f"[CardSVG] load_svg_content called with: {content[:100]}")
        
        # Encode image file as data URL if an image path is provided
        image_data_url = ""
        if content.lower().endswith((".jpg", ".jpeg", ".png")):
            try:
                img_path = Path(content)
                if img_path.exists():
                    with open(img_path, 'rb') as f:
                        img_bytes = f.read()
                    b64 = base64.b64encode(img_bytes).decode('ascii')
                    ext = img_path.suffix.lower()
                    mime = 'image/jpeg' if ext in ['.jpg', '.jpeg'] else 'image/png'
                    image_data_url = f"data:{mime};base64,{b64}"
                    logger.info(f"[CardSVG] Loaded image from {content}, size: {len(img_bytes)} bytes")
            except Exception as e:
                logger.error(f"[CardSVG] Failed to load image: {e}")
        
        # If input looks like raw SVG, render directly; else wrap image into SVG layout
        if "<svg" in content[:200]:
            svg = content
        else:
            if image_data_url:
                image_tag = (
                    f'<image x="430" y="30" width="340" height="540" '
                    f'href="{image_data_url}" preserveAspectRatio="xMidYMid meet"/>'
                )
            else:
                image_tag = (
                    '<rect x="530" y="230" width="140" height="140" rx="10" fill="#ddd" stroke="#999" stroke-width="2"/>'
                    '<text x="600" y="305" font-family="Arial" font-size="48" fill="#999" text-anchor="middle">🖼️</text>'
                    '<text x="600" y="340" font-family="Arial" font-size="14" fill="#666" text-anchor="middle">Image Area</text>'
                )
            svg = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<svg width="800" height="600" viewBox="0 0 800 600" xmlns="http://www.w3.org/2000/svg">\n'
                '  <defs>\n'
                '    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">\n'
                '      <stop offset="0%" style="stop-color:#667eea;stop-opacity:1" />\n'
                '      <stop offset="100%" style="stop-color:#764ba2;stop-opacity:1" />\n'
                '    </linearGradient>\n'
                '  </defs>\n'
                '  <rect width="800" height="600" fill="url(#bg)"/>\n'
                '  <rect x="20" y="20" width="360" height="560" rx="10" fill="white" fill-opacity="0.95" stroke="#4a4a4a" stroke-width="2"/>\n'
                '  <text x="200" y="70" font-family="Arial, sans-serif" font-size="32" font-weight="bold" fill="#333" text-anchor="middle" textLength="340" lengthAdjust="spacingAndGlyphs">SVG Layout Demo</text>\n'
                '  <text x="200" y="100" font-family="Arial, sans-serif" font-size="14" fill="#666" text-anchor="middle" textLength="330" lengthAdjust="spacing">Responsive text scaling demonstration</text>\n'
                '  <rect x="420" y="20" width="360" height="560" rx="10" fill="white" fill-opacity="0.95" stroke="#4a4a4a" stroke-width="2"/>\n'
                f'  {image_tag}\n'
                '</svg>'
            )
        
        self._view.load(QtCore.QByteArray(svg.encode('utf-8')))
        logger.info(f"[CardSVG] SVG content loaded into QSvgWidget")
    
    def showEvent(self, event):
        super().showEvent(event)
        logger.info(f"[CardSVG] showEvent: size = {self.size()}, view size = {self._view.size()}")

    def call(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        args = arguments or {}
        if name == "open_url":
            self.load_svg_content(str(args.get("url", "")))
            return {"status": "ok", "url": args.get("url")}
        raise ValueError(f"Unsupported function: {name}")

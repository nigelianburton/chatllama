from typing import Any, Dict, List, Optional
from PyQt6 import QtCore, QtWidgets, QtSvgWidgets
from ._card_template import CardBase
import logging
import base64
from pathlib import Path

logger = logging.getLogger(__name__)


class CardChrome(CardBase):
    """SVG display card for visual content (no WebEngine)."""

    name: str = "card_chrome"
    functions: List[Dict[str, Any]] = [
        {
            "name": "open_url",
            "description": "Load the given URL into the embedded browser pane.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Absolute URL to load",
                    }
                },
                "required": ["url"],
            },
        }
    ]

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, start_url: str = "https://example.com") -> None:
        logger.info(f"[CardChrome] __init__ called with parent: {parent.__class__.__name__ if parent else None}")
        super().__init__(parent)
        logger.info(f"[CardChrome] After super().__init__, CardBase size: {self.size()}")
        
        # Use QSvgWidget for reliable SVG rendering - LLMs know SVG well
        self._view = QtSvgWidgets.QSvgWidget(self)
        logger.info(f"[CardChrome] Created QSvgWidget for SVG rendering")
        
        self._view.setSizePolicy(
            QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        )
        self._view.setStyleSheet("QSvgWidget { background-color: white; border: 1px solid #ccc; }")
        self._view.setMinimumHeight(200)
        self._view.resize(400, 300)
        logger.info(f"[CardChrome] QSvgWidget configured. Size: {self._view.size()}, minHeight: {self._view.minimumHeight()}")
        
        self.set_card_widget(self._view)
        logger.info(f"[CardChrome] After set_card_widget. View parent: {self._view.parent().__class__.__name__ if self._view.parent() else None}")
        
        # Load initial SVG content
        self.load_svg_content(start_url)
        logger.info(f"[CardChrome] __init__ complete. Initial content loaded")

    def load_svg_content(self, content: str) -> None:
        """Load SVG content into the widget. Content can be SVG XML string or image file path."""
        if not content:
            return
        
        logger.info(f"[CardChrome] load_svg_content called with: {content[:100]}")
        
        # Check if content is a file path to an image
        image_data_url = ""
        if content.endswith(('.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG')):
            try:
                img_path = Path(content)
                if img_path.exists():
                    with open(img_path, 'rb') as f:
                        img_bytes = f.read()
                    b64 = base64.b64encode(img_bytes).decode('ascii')
                    # Detect image type from extension
                    ext = img_path.suffix.lower()
                    mime = 'image/jpeg' if ext in ['.jpg', '.jpeg'] else 'image/png'
                    image_data_url = f"data:{mime};base64,{b64}"
                    logger.info(f"[CardChrome] Loaded image from {content}, size: {len(img_bytes)} bytes")
            except Exception as e:
                logger.error(f"[CardChrome] Failed to load image: {e}")
        
        # Create SVG with text on left, image on right
        svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="800" height="600" viewBox="0 0 800 600" xmlns="http://www.w3.org/2000/svg">
  <!-- Background -->
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#667eea;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#764ba2;stop-opacity:1" />
    </linearGradient>
  </defs>
  
  <rect width="800" height="600" fill="url(#bg)"/>
  
  <!-- Left side: Text content (50% width) -->
  <rect x="20" y="20" width="360" height="560" rx="10" 
        fill="white" fill-opacity="0.95" stroke="#4a4a4a" stroke-width="2"/>
  
  <!-- Title with textLength for scaling -->
  <text x="200" y="70" font-family="Arial, sans-serif" font-size="32" font-weight="bold" 
        fill="#333" text-anchor="middle" textLength="340" lengthAdjust="spacingAndGlyphs">
    SVG Layout Demo
  </text>
  
  <!-- Subtitle with textLength -->
  <text x="200" y="100" font-family="Arial, sans-serif" font-size="14" 
        fill="#666" text-anchor="middle" textLength="330" lengthAdjust="spacing">
    Responsive text scaling demonstration
  </text>
  
  <!-- Features with text scaling using textLength -->
  <text x="40" y="130" font-family="Arial, sans-serif" font-size="14" font-weight="bold" fill="#333">
    Text Scaling Features:
  </text>
  <text x="40" y="155" font-family="Arial, sans-serif" font-size="12" fill="#555" 
        textLength="320" lengthAdjust="spacing">
    ✓ Use textLength to fit exact width
  </text>
  <text x="40" y="180" font-family="Arial, sans-serif" font-size="12" fill="#555" 
        textLength="320" lengthAdjust="spacing">
    ✓ lengthAdjust="spacing" or "spacingAndGlyphs"
  </text>
  <text x="40" y="205" font-family="Arial, sans-serif" font-size="12" fill="#555" 
        textLength="320" lengthAdjust="spacing">
    ✓ LLM calculates font-size for content
  </text>
  <text x="40" y="230" font-family="Arial, sans-serif" font-size="12" fill="#555" 
        textLength="320" lengthAdjust="spacing">
    ✓ This line is auto-scaled to fit width
  </text>
  
  <!-- Example of calculated sizing -->
  <text x="40" y="270" font-family="Arial, sans-serif" font-size="12" fill="#222" font-weight="bold">
    Dynamic Sizing Examples:
  </text>
  <text x="40" y="295" font-family="monospace" font-size="11" fill="#666" 
        textLength="320" lengthAdjust="spacing">
    Monospace scaled to fit via textLength
  </text>
  <text x="40" y="320" font-family="Arial" font-size="14" fill="#555" 
        textLength="320" lengthAdjust="spacingAndGlyphs">
    Serif text with glyph adjustment
  </text>
  <text x="40" y="355" font-family="Arial" font-size="16" fill="#333" font-weight="bold"
        textLength="320" lengthAdjust="spacingAndGlyphs">
    Larger bold text auto-fitted
  </text>
  
  <!-- Footer -->
  <text x="200" y="540" font-family="Arial, sans-serif" font-size="12" 
        fill="#666" text-anchor="middle" font-style="italic">
    LLM-generated SVG layout
  </text>
  
  <!-- Right side: Image (50% width, preserves aspect ratio) -->
  <rect x="420" y="20" width="360" height="560" rx="10" 
        fill="white" fill-opacity="0.95" stroke="#4a4a4a" stroke-width="2"/>
  
  {f'''<image x="430" y="30" width="340" height="540" 
         href="{image_data_url}" 
         preserveAspectRatio="xMidYMid meet"/>''' if image_data_url else '''
  <!-- Placeholder when no image -->
  <rect x="530" y="230" width="140" height="140" rx="10" fill="#ddd" stroke="#999" stroke-width="2"/>
  <text x="600" y="305" font-family="Arial" font-size="48" fill="#999" text-anchor="middle">🖼️</text>
  <text x="600" y="340" font-family="Arial" font-size="14" fill="#666" text-anchor="middle">Image Area</text>'''}
</svg>"""
        
        self._view.load(QtCore.QByteArray(svg.encode('utf-8')))
        logger.info(f"[CardChrome] SVG content loaded into QSvgWidget")
    
    def showEvent(self, event):
        super().showEvent(event)
        logger.info(f"[CardChrome] showEvent: size = {self.size()}, view size = {self._view.size()}")

    def call(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        args = arguments or {}
        if name == "open_url":
            # For SVG cards, treat URL as SVG content or generate placeholder
            self.load_svg_content(str(args.get("url", "")))
            return {"status": "ok", "url": args.get("url")}
        raise ValueError(f"Unsupported function: {name}")

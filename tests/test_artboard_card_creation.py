"""Test artboard creation with CardBase + CardSVG instantiation."""

import sys
import logging
import os
from pathlib import Path

# Set Qt to use offscreen platform for headless testing
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Create QApplication before importing PyQt widgets
from PyQt6.QtWidgets import QApplication
app = QApplication(sys.argv) if not QApplication.instance() else QApplication.instance()

from mcp_http_server import SVGLayoutStudioMCP
from cards.card_svg import CardSVG
from cards._card_template import CardBase


def test_artboard_card_creation():
    """Test that create_artboard instantiates CardBase with CardSVG inside."""
    
    print("\n" + "="*80)
    print("TEST: Artboard Creation with CardBase + CardSVG")
    print("="*80)
    
    # Track created cards
    created_cards = {}
    
    def ui_create_card(title: str) -> CardSVG:
        """Simulate UI card creation callback."""
        card = CardBase()
        svg_widget = CardSVG(parent=card)
        card.set_card_widget(svg_widget)
        
        created_cards[title] = {
            'card': card,
            'svg_widget': svg_widget,
        }
        
        print(f"\n✓ Created card: {title}")
        print(f"  - CardBase instance: {card.__class__.__name__}")
        print(f"  - CardSVG instance: {svg_widget.__class__.__name__}")
        print(f"  - CardSVG parent: {svg_widget.parent().__class__.__name__}")
        
        return svg_widget
    
    def ui_display_svg(svg: str) -> None:
        """Fallback SVG display (not used in this test)."""
        pass
    
    # Initialize MCP with callbacks
    rules_path = PROJECT_ROOT / "src" / "cards" / "svg_generation_rules.json"
    mcp = SVGLayoutStudioMCP(
        ui_display_svg=ui_display_svg,
        ui_create_card=ui_create_card,
        rules_path=rules_path
    )
    
    print("\n[Step 1] Creating portrait artboard...")
    result = mcp.call_tool("create_artboard", {"orientation": "portrait"})
    
    if result and "artboard_guid" in result:
        artboard_guid = result["artboard_guid"]
        print(f"✓ Artboard created: {artboard_guid}")
        print(f"  - Dimensions: {result['width']}×{result['height']}")
        print(f"  - Stored in MCP: {'artboard_guid' in mcp._artboards}")
        
        # Verify card was created
        if "Artboard Portrait" in created_cards:
            card_data = created_cards["Artboard Portrait"]
            print(f"✓ Card instantiation verified:")
            print(f"  - CardBase: {card_data['card']}")
            print(f"  - CardSVG: {card_data['svg_widget']}")
        else:
            print("✗ Card was not created!")
            return False
    else:
        print(f"✗ Artboard creation failed: {result}")
        return False
    
    print("\n[Step 2] Rendering SVG to artboard...")
    blue_box_svg = """<svg viewBox="0 0 1000 1400" xmlns="http://www.w3.org/2000/svg">
  <rect width="1000" height="1400" fill="#f5f5f5"/>
  <rect x="250" y="500" width="500" height="400" fill="#0066cc"/>
  <text x="500" y="750" font-family="Arial" font-size="20" fill="white" text-anchor="middle">Blue Box</text>
</svg>"""
    
    render_result = mcp.call_tool("render_svg", {
        "artboard_guid": artboard_guid,
        "svg": blue_box_svg
    })
    
    if render_result and render_result.get("status") == "ok":
        print(f"✓ SVG rendered successfully")
        print(f"  - Content length: {render_result['length']} chars")
        
        # Verify CardSVG was updated
        card_data = created_cards["Artboard Portrait"]
        if hasattr(card_data['svg_widget'], '_view'):
            print(f"✓ CardSVG._view accessible for SVG rendering")
        
        print("\n" + "="*80)
        print("✅ TEST PASSED: Artboard creates CardBase with CardSVG inside")
        print("="*80 + "\n")
        return True
    else:
        print(f"✗ SVG render failed: {render_result}")
        return False


def test_landscape_artboard():
    """Test landscape artboard creation."""
    
    print("\n" + "="*80)
    print("TEST: Landscape Artboard Creation")
    print("="*80)
    
    created_cards = {}
    
    def ui_create_card(title: str) -> CardSVG:
        card = CardBase()
        svg_widget = CardSVG(parent=card)
        card.set_card_widget(svg_widget)
        created_cards[title] = {'card': card, 'svg_widget': svg_widget}
        print(f"\n✓ Created: {title}")
        return svg_widget
    
    def ui_display_svg(svg: str) -> None:
        pass
    
    rules_path = PROJECT_ROOT / "src" / "cards" / "svg_generation_rules.json"
    mcp = SVGLayoutStudioMCP(
        ui_display_svg=ui_display_svg,
        ui_create_card=ui_create_card,
        rules_path=rules_path
    )
    
    result = mcp.call_tool("create_artboard", {"orientation": "landscape"})
    
    if result:
        print(f"✓ Landscape artboard: {result['width']}×{result['height']}")
        if "Artboard Landscape" in created_cards:
            print("✓ Card created for landscape orientation")
            print("\n" + "="*80)
            print("✅ TEST PASSED: Landscape artboard")
            print("="*80 + "\n")
            return True
    
    print("✗ Landscape test failed")
    return False


if __name__ == "__main__":
    success = True
    success = test_artboard_card_creation() and success
    success = test_landscape_artboard() and success
    
    if success:
        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED")
        print("="*80 + "\n")
        sys.exit(0)
    else:
        print("\n" + "="*80)
        print("❌ SOME TESTS FAILED")
        print("="*80 + "\n")
        sys.exit(1)

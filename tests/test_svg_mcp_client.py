#!/usr/bin/env python3
"""
Test client for SVGLayoutStudioMCP using fastmcp.

This demonstrates:
1) Getting tool advertisements from the MCP
2) Calling tools to create artboards and render SVG
"""

import asyncio
import json
from pathlib import Path
from typing import Any

# For direct local testing, we can also import the server directly
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_http_server import SVGLayoutStudioMCP


class SVGClientTester:
    """Test client for SVG MCP."""
    
    def __init__(self):
        self.mcp = None
        
    def setup_mcp(self):
        """Initialize the MCP server locally."""
        def dummy_ui(svg: str):
            """Dummy UI callback - just print."""
            print(f"\n[UI CALLBACK] Received SVG ({len(svg)} chars)")
            print("SVG content (first 200 chars):")
            print(svg[:200] + "..." if len(svg) > 200 else svg)
        
        rules_path = Path(__file__).parent.parent / "src" / "cards" / "svg_generation_rules.json"
        self.mcp = SVGLayoutStudioMCP(
            ui_display_svg=dummy_ui,
            rules_path=rules_path,
            host="127.0.0.1",
            port=6821
        )
        return self.mcp
    
    def test_tool_discovery(self):
        """Test 1: Get tool advertisements."""
        print("\n" + "="*80)
        print("TEST 1: TOOL DISCOVERY (Advertising)")
        print("="*80)
        
        config = self.mcp.get_server_config()
        print("\nServer Configuration:")
        print(json.dumps(config, indent=2))
        
        tools = self.mcp.get_tools()
        print(f"\nAdvertised Tools: {len(tools)}")
        for tool in tools:
            print(f"\n  • {tool['name']}")
            print(f"    Description: {tool['description'][:100]}...")
            print(f"    Parameters:")
            props = tool['inputSchema'].get('properties', {})
            for param, schema in props.items():
                print(f"      - {param} ({schema.get('type', 'unknown')}): {schema.get('description', 'No description')[:80]}...")
    
    def test_create_artboard(self):
        """Test 2: Create an artboard."""
        print("\n" + "="*80)
        print("TEST 2: CREATE ARTBOARD")
        print("="*80)
        
        result = self.mcp.call_tool("create_artboard", {
            "orientation": "portrait"
        })
        
        print("\nCreate Artboard Result:")
        print(json.dumps(result, indent=2))
        
        return result.get("artboard_guid")
    
    def test_render_svg(self, artboard_guid: str):
        """Test 3: Render SVG."""
        print("\n" + "="*80)
        print("TEST 3: RENDER SVG")
        print("="*80)
        
        simple_svg = f'''<svg viewBox="0 0 1000 1400" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      .title {{ font-size: 48px; font-weight: bold; fill: #333; }}
      .subtitle {{ font-size: 24px; fill: #666; }}
      .box {{ fill: #e8f4f8; stroke: #0066cc; stroke-width: 2; }}
    </style>
  </defs>
  
  <!-- Background -->
  <rect width="1000" height="1400" fill="#ffffff"/>
  
  <!-- Title Box -->
  <rect class="box" x="50" y="50" width="900" height="200" rx="10"/>
  <text class="title" x="500" y="140" text-anchor="middle">SVG Layout Test</text>
  <text class="subtitle" x="500" y="180" text-anchor="middle">Created via MCP</text>
  
  <!-- Content Area -->
  <rect class="box" x="50" y="280" width="900" height="500" rx="10"/>
  <text class="subtitle" x="500" y="350" text-anchor="middle">Content Area</text>
  <text style="font-size: 16px; fill: #999;" x="500" y="450" text-anchor="middle">This SVG was generated and rendered via the SVGLayoutStudioMCP</text>
  
  <!-- Footer -->
  <rect x="50" y="1250" width="900" height="100" fill="#f0f0f0" rx="10"/>
  <text style="font-size: 14px; fill: #666;" x="500" y="1310" text-anchor="middle">Footer - Artboard GUID: {artboard_guid[:8]}...</text>
</svg>'''
        
        result = self.mcp.call_tool("render_svg", {
            "artboard_guid": artboard_guid,
            "svg": simple_svg
        })
        
        print("\nRender SVG Result:")
        print(json.dumps(result, indent=2))
        
        return result
    
    def test_list_capabilities(self):
        """Test 4: List SVG capabilities."""
        print("\n" + "="*80)
        print("TEST 4: LIST SVG CAPABILITIES")
        print("="*80)
        
        result = self.mcp.call_tool("list_svg_capabilities", {})
        
        print("\nCapabilities:")
        if result:
            print(json.dumps(result, indent=2))
        else:
            print("(No result returned)")
    
    async def run_all_tests(self):
        """Run all tests in sequence."""
        print("\n" + "#"*80)
        print("# SVG MCP CLIENT TEST SUITE")
        print("#"*80)
        
        # Setup
        self.setup_mcp()
        
        # Test 1: Discovery
        self.test_tool_discovery()
        
        # Test 2: Create artboard
        artboard_guid = self.test_create_artboard()
        
        # Test 3: Render SVG
        if artboard_guid:
            self.test_render_svg(artboard_guid)
        
        # Test 4: Capabilities
        self.test_list_capabilities()
        
        print("\n" + "#"*80)
        print("# ALL TESTS COMPLETE")
        print("#"*80 + "\n")


async def main():
    """Run the test client."""
    tester = SVGClientTester()
    
    print("\n" + "#"*80)
    print("# SVG MCP - CREATE ARTBOARD & RENDER BLUE BOX")
    print("#"*80 + "\n")
    
    # Setup
    tester.setup_mcp()
    
    # Create artboard
    print("Creating portrait artboard...")
    result = tester.mcp.call_tool("create_artboard", {"orientation": "portrait"})
    artboard_guid = result.get("artboard_guid")
    width = result.get("width", 1000)
    height = result.get("height", 1400)
    print(f"✓ Artboard created: {artboard_guid}")
    print(f"  Dimensions: {width}×{height}\n")
    
    # Create SVG with blue box
    print("Generating SVG with blue box...")
    blue_box_svg = f'''<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <!-- Background -->
  <rect width="{width}" height="{height}" fill="#f5f5f5"/>
  
  <!-- Blue box centered -->
  <rect x="250" y="500" width="500" height="400" fill="#0066cc" rx="10"/>
  
  <!-- Text inside box -->
  <text x="500" y="650" font-size="48" fill="white" text-anchor="middle" font-weight="bold">
    Blue Box
  </text>
  <text x="500" y="720" font-size="24" fill="white" text-anchor="middle">
    Created via SVG MCP
  </text>
</svg>'''
    
    # Render it
    print("Rendering SVG to UI...\n")
    render_result = tester.mcp.call_tool("render_svg", {
        "artboard_guid": artboard_guid,
        "svg": blue_box_svg
    })
    
    print(f"✓ SVG rendered successfully!")
    print(f"  Status: {render_result.get('status')}")
    print(f"  Content length: {render_result.get('length')} characters\n")
    print("#"*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

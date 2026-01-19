"""
FastMCP client test - connect to running SVG MCP server and test artboard creation.
Does NOT create its own server, just calls the running one.

The chat.py app must be running (it will automatically start the MCP server):
    python src/chat.py
"""

import json
import requests
import time
import sys

def test_svg_mcp_client():
    """Connect to running SVG MCP server and test artboard + rendering."""
    
    # The server should be running at http://127.0.0.1:6821
    server_url = "http://127.0.0.1:6821"
    
    print("=" * 80)
    print("SVG MCP CLIENT - ARTBOARD CREATION TEST")
    print("=" * 80)
    print(f"\nConnecting to MCP server at {server_url}...")
    
    # Wait for server to be ready (with timeout)
    max_retries = 5
    for attempt in range(max_retries):
        try:
            resp = requests.get(f"{server_url}/health", timeout=2)
            if resp.status_code == 200:
                print(f"✓ Server is ready!\n")
                break
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"\n✗ ERROR: Could not connect to MCP server at {server_url}")
                print(f"  Make sure chat.py is running: python src/chat.py")
                return
            time.sleep(0.5)
    
    # Step 1: Create artboard
    print("[1] Creating portrait artboard...")
    artboard_response = requests.post(
        f"{server_url}/tools/create_artboard",
        json={"orientation": "portrait"}
    )
    
    if artboard_response.status_code != 200:
        print(f"ERROR: {artboard_response.text}")
        return
    
    artboard_data = artboard_response.json()
    artboard_guid = artboard_data.get("artboard_guid")
    width = artboard_data.get("width")
    height = artboard_data.get("height")
    
    print(f"✓ Artboard created: {artboard_guid}")
    print(f"  Dimensions: {width}×{height}")
    
    # Step 2: Create greeting card SVG
    print("\n[2] Creating greeting card SVG design...")
    svg_content = f"""<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <!-- Gradient background -->
  <defs>
    <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#667eea;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#764ba2;stop-opacity:1" />
    </linearGradient>
  </defs>
  
  <!-- Background -->
  <rect width="{width}" height="{height}" fill="url(#grad1)"/>
  
  <!-- Decorative circles -->
  <circle cx="100" cy="100" r="80" fill="#ffffff" opacity="0.1"/>
  <circle cx="{width-100}" cy="{height-100}" r="120" fill="#ffffff" opacity="0.1"/>
  
  <!-- Main greeting card box -->
  <rect x="150" y="400" width="{width-300}" height="500" fill="white" rx="20" opacity="0.95"/>
  
  <!-- Main text -->
  <text x="{width//2}" y="550" font-size="72" font-weight="bold" text-anchor="middle" fill="#667eea">
    Hello World!
  </text>
  
  <!-- Subtitle -->
  <text x="{width//2}" y="680" font-size="28" text-anchor="middle" fill="#764ba2">
    Welcome to SVG Artboards
  </text>
  
  <!-- Decorative line -->
  <line x1="250" y1="720" x2="{width-250}" y2="720" stroke="#667eea" stroke-width="3" opacity="0.5"/>
  
  <!-- Footer text -->
  <text x="{width//2}" y="800" font-size="16" text-anchor="middle" fill="#999">
    Generated via MCP Artboard API
  </text>
</svg>"""
    
    # Step 3: Render SVG to artboard
    print("\n[3] Rendering SVG to artboard...")
    render_response = requests.post(
        f"{server_url}/tools/render_svg",
        json={
            "artboard_guid": artboard_guid,
            "svg": svg_content
        }
    )
    
    if render_response.status_code != 200:
        print(f"ERROR: {render_response.text}")
        return
    
    render_data = render_response.json()
    print(f"✓ SVG rendered successfully!")
    print(f"  Status: {render_data.get('status')}")
    print(f"  Content length: {render_data.get('length')} characters")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE - Check the Cards panel in the app to see the greeting card!")
    print("=" * 80)

if __name__ == "__main__":
    test_svg_mcp_client()

"""Test script to verify built-in MCP integration.

Run with: python tests/test_builtin_mcp.py
Or via chat: python src/chat.py --mcp-http
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_http_server import SVGLayoutStudioMCP

def test_server_config():
    """Test server configuration format."""
    def dummy_ui(svg):
        print(f"UI render called with {len(svg)} chars")
    
    rules_path = Path(__file__).parent.parent / "src" / "cards" / "svg_generation_rules.json"
    srv = SVGLayoutStudioMCP(ui_display_svg=dummy_ui, rules_path=rules_path)
    
    config = srv.get_server_config()
    print("\n=== Server Config ===")
    print(f"Name: {config.get('name')}")
    print(f"Type: {config.get('type')}")
    print(f"URL: {config.get('url')}")
    print(f"Description: {config.get('description')}")
    
    assert config.get("name") == "svg-layout-studio"
    assert config.get("type") == "builtin"
    assert "http://" in config.get("url", "")
    print("✓ Server config valid")

def test_tools():
    """Test tool definitions."""
    def dummy_ui(svg):
        pass
    
    rules_path = Path(__file__).parent.parent / "src" / "cards" / "svg_generation_rules.json"
    srv = SVGLayoutStudioMCP(ui_display_svg=dummy_ui, rules_path=rules_path)
    
    tools = srv.get_tools()
    print(f"\n=== Tools ({len(tools)}) ===")
    for tool in tools:
        print(f"\n{tool.get('name')}:")
        print(f"  Description: {tool.get('description')[:80]}...")
        schema = tool.get("inputSchema", {})
        props = schema.get("properties", {})
        print(f"  Parameters: {list(props.keys())}")
    
    assert len(tools) == 3
    assert any(t.get("name") == "create_artboard" for t in tools)
    assert any(t.get("name") == "render_svg" for t in tools)
    print("\n✓ All tools present and valid")

if __name__ == "__main__":
    print("Testing built-in MCP integration...")
    test_server_config()
    test_tools()
    print("\n✅ All tests passed!")
    print("\nTo test in the UI:")
    print("  python src/chat.py --mcp-http")
    print("  Check Settings panel for 'svg-layout-studio' MCP")

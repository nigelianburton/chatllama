# Built-in MCP: SVG Layout Studio

ChatLlama includes a built-in MCP server that allows LLMs to generate SVG page layouts and render them directly into the Cards panel.

## Features

- **Automatic Discovery**: Built-in MCPs appear in Settings alongside external MCPs from `settings.yml`
- **Tool Advertising**: Tools are automatically advertised to the loaded LLM in the system prompt
- **Standard MCP Protocol**: Uses FastMCP decorators, same as external servers
- **UI Integration**: Renders SVG directly into the Cards panel via thread-safe dispatch

## Architecture

### Server Class: `SVGLayoutStudioMCP`

Located in [`src/mcp_http_server.py`](../src/mcp_http_server.py)

- Runs FastMCP HTTP server in background thread
- Exposes 3 tools via MCP protocol
- Provides `get_server_config()` for Settings panel integration
- Provides `get_tools()` for tool advertising to LLM

### Tools

1. **`create_artboard(orientation, width, height)`**
   - First step: creates canvas and returns GUID
   - Attaches SVG generation rules JSON (only when requested)
   - Returns: `{artboard_guid, width, height, orientation, viewBox, rules}`

2. **`render_svg(artboard_guid, svg)`**
   - Renders SVG markup into Cards panel
   - Thread-safe UI dispatch via `QtCore.QTimer.singleShot`
   - Returns: `{status, artboard_guid, length}`

3. **`list_svg_capabilities()`**
   - Discovery tool for LLMs
   - Returns list of available tools and their requirements

### SVG Generation Rules

Stored in [`src/cards/svg_generation_rules.json`](../src/cards/svg_generation_rules.json)

Directive rules to prevent common small-model SVG errors:
- viewBox syntax (must start "0 0")
- No math expressions in attributes
- Image fill dimensions
- Text centering with `text-anchor="middle"`
- Layering order (background first, foreground last)

Attached only on `create_artboard` response to minimize token usage.

## Usage

### Command Line

Start the UI with built-in MCP server:

```powershell
python src/chat.py --mcp-http
```

Custom port:

```powershell
python src/chat.py --mcp-http --mcp-http-port 6821
```

### Settings Panel

Built-in MCP appears automatically in the Settings column:

- **Name**: svg-layout-studio
- **Type**: builtin
- **Transport**: HTTP (SSE)
- **Tools**: 3 (create_artboard, render_svg, list_svg_capabilities)

### LLM Interaction

When tool integration is enabled (`tool_integration_enabled: true` in `settings.yml`), the LLM will see:

```
You have access to specialized tools...
```

Example tool usage by LLM:

1. **Create artboard**:
   ```
   [TOOL_REQUEST]{"name": "create_artboard", "arguments": {"orientation": "portrait"}}[END_TOOL_REQUEST]
   ```

2. **Render SVG**:
   ```
   [TOOL_REQUEST]{"name": "render_svg", "arguments": {"artboard_guid": "abc-123", "svg": "<svg>...</svg>"}}[END_TOOL_REQUEST]
   ```

## Integration Points

### SettingsPanel (`src/chatllama_pane_settings.py`)

- `register_builtin_mcp(server_config)` - Adds built-in MCP panel to UI
- Creates `McpInfoPanel` for built-in server
- Displays tools and allows manual testing

### ChatWindow (`src/chat.py`)

- `start_built_in_mcp_http()` - Starts server and registers with Settings
- `_integrate_builtin_mcp_tools()` - Merges tools with external MCPs
- `_fetch_and_integrate_tools()` - Includes built-in tools in system prompt

### CardsPanel (`src/chatllama_pane_cards.py`)

- `display_svg(svg_markup)` - Renders SVG via CardChrome
- Thread-safe: called from main UI thread

## Testing

Run the test suite:

```powershell
python tests/test_builtin_mcp.py
```

Test in the UI:

1. Start with `--mcp-http` flag
2. Check Settings panel for "svg-layout-studio" MCP
3. Select a tool and click "Call" to test manually
4. Or load a capable model and ask it to create an SVG layout

## Extension

To add more built-in MCPs:

1. Create a new class similar to `SVGLayoutStudioMCP`
2. Implement:
   - `get_server_config()` → returns config dict
   - `get_tools()` → returns tool definitions
   - `start()` → starts the server
3. Register in `ChatWindow.__init__()` or via CLI flag
4. Call `_settings_panel.register_builtin_mcp(config)`

## Notes

- Built-in MCPs run in-process, no external process spawning
- Thread-safe: server runs in background, UI updates on main thread
- No settings.yml entry required (unlike external MCPs)
- Automatically advertised to LLM when tool integration is enabled
- Uses same MCP protocol as external servers (FastMCP)

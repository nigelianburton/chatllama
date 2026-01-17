# MCP Tool Integration in ChatLlama

## Overview

ChatLlama now properly implements the Model Context Protocol (MCP) standard for tool discovery and integration. When an MCP server is running, ChatLlama uses the standard MCP `tools/list` protocol endpoint to fetch tool definitions and includes them in the system prompt.

## How It Works

### Startup Sequence

1. **UI Initialization**: ChatLlama builds the user interface
2. **MCP Server Launch**: Launches the MCP server as a subprocess (stdio transport)
3. **MCP Connection**: Connects to server via stdio pipes
4. **Tool Discovery**: Calls MCP `tools/list` endpoint to get available tools
5. **Prompt Integration**: Formats tools into the system prompt
6. **Model Loading**: Loads the default language model

### MCP Protocol Flow

```
ChatLlama                          MCP Server
    |                                  |
    |--- spawn process (stdio) ------->|
    |                                  |
    |--- session.list_tools() -------->|
    |                                  |
    |<---- tools/list response --------|
    |                                  |
    |--- format & integrate tools ------|
    |                                  |
```

### Tool Advertisement

Tools are advertised via the standard MCP `tools/list` endpoint. The response includes:
- **Tool Name**: Function name (from `@server.tool()` decorator)
- **Description**: Docstring from the function
- **Input Schema**: JSON Schema derived from type annotations

Example tool from fashion-curator MCP:
```python
@server.tool()
def get_personalized_recommendation(user_id: str) -> dict:
    """Get a personalized fashion look based on user preferences."""
    return curator.get_personalized_look(user_id)
```

This automatically generates:
```json
{
  "name": "get_personalized_recommendation",
  "description": "Get a personalized fashion look based on user preferences.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "user_id": {"type": "string", "description": "..."}
    }
  }
}
```

### System Prompt Integration

The tools are formatted into the system prompt using a preamble template. The model can then suggest using these tools when appropriate.

**Example System Prompt:**
```
You are a helpful assistant.

You have access to specialized tools that extend your capabilities.

Tools Available:
  • get_personalized_recommendation: Get a personalized fashion look based on user preferences.
  • save_favorite_look: Save a fashion look to user's favorites.
  • list_all_looks: List all available fashion looks for 2026.

When a user request requires using a tool, you can suggest using it.
Format: TOOL: [tool_name] with [param1=value1, param2=value2, ...]

Use tools proactively when they would enhance your response to the user.
```

## Configuration

Settings are in `settings.yml`:

```yaml
# MCP Server Configuration
mcp_server_enabled: true
mcp_server_command: "python test_mcp/fashion_server/server.py"

# System prompt preamble for tool/MCP integration
tool_integration_enabled: true
tool_preamble: |
  You have access to specialized tools...
  {tools_list}
```

### Key Settings

- **`mcp_server_enabled`**: Enable/disable MCP server integration (default: true)
- **`mcp_server_command`**: Command to launch MCP server (default: python test_mcp/fashion_server/server.py)
- **`tool_integration_enabled`**: Include tools in system prompt (default: true)
- **`tool_preamble`**: Template for tool descriptions (use `{tools_list}` placeholder)

## Implementation Details

### MCP Server Requirements

For an MCP server to work with ChatLlama:

1. **Use fastmcp**: Build server with `from fastmcp import FastMCP`
2. **Register Tools**: Use `@server.tool()` decorator on functions
3. **Type Annotations**: Add Python type hints for parameters
4. **Docstrings**: Provide docstrings for description

```python
from fastmcp import FastMCP

server = FastMCP("my-server")

@server.tool()
def my_tool(param1: str, param2: int) -> dict:
    """Description of what this tool does."""
    return {"result": "..."}

if __name__ == "__main__":
    server.run()  # Runs with stdio transport
```

### ChatLlama MCP Client

ChatLlama implements an MCP client that:

1. **Spawns MCP Server**: Launches process with stdio pipes
2. **Creates Session**: Establishes async session over stdio
3. **Lists Tools**: Calls `session.list_tools()` (standard MCP endpoint)
4. **Extracts Metadata**: Gets name, description, and schema
5. **Formats for Prompt**: Creates bullet-list of tools

**Key Methods:**
- `_launch_mcp_server()` - Spawns server process
- `_is_mcp_server_running()` - Checks if process is alive
- `_fetch_mcp_tools()` - Calls MCP `tools/list` endpoint
- `_format_tools_for_prompt()` - Formats tools for system prompt
- `_fetch_and_integrate_tools()` - Orchestrates the flow

## Standard MCP vs Custom HTTP

### ✅ ChatLlama's Approach (Standard MCP)
- Uses stdio transport (process pipes)
- Connects via MCP protocol (not HTTP)
- Calls standard `tools/list` endpoint
- Works with any MCP-compliant server
- No custom HTTP endpoints needed

### ❌ Previous Custom HTTP Approach
- Created custom `/tools` HTTP endpoint
- Required running HTTP server
- Non-standard protocol
- Tightly coupled implementation

## Built-in MCP Servers

### fashion-curator (Stateful Server)

**Location**: `test_mcp/fashion_server/server.py`

**Transport**: stdio (MCP protocol)

**Tools**:
```python
@server.tool()
def create_user_profile(user_id: str, favorite_vibes: list[str]) -> dict: ...

@server.tool()
def get_personalized_recommendation(user_id: str) -> dict: ...

@server.tool()
def save_favorite_look(user_id: str, look_id: int) -> dict: ...

@server.tool()
def get_user_saved_looks(user_id: str) -> dict: ...

@server.tool()
def get_user_statistics(user_id: str) -> dict: ...

@server.tool()
def list_all_looks() -> dict: ...
```

### fashion-advisor (Stateless)

**Location**: `test_mcp/fashion_stdio.py`

**Transport**: stdio (MCP protocol)

**Tools**:
```python
@server.tool()
def get_fashion_look() -> dict: ...

@server.tool()
def get_all_looks() -> dict: ...

@server.tool()
def get_look_by_vibe(vibe: str) -> dict: ...
```

## Future Tool Execution

Currently, ChatLlama advertises tools to the model so it can suggest them. Future versions can implement:

1. **Parse Model Output**: Detect TOOL: suggestions in model responses
2. **Execute Tool**: Call the MCP tool with suggested parameters
3. **Feed Results Back**: Include tool output in conversation context

This enables full agentic behavior where the model can request tool execution.

## Troubleshooting

### Tools Not Appearing

Check logs in `chatllama.log`:
- "MCP server not available for tool fetching" - Server not running
- "Failed to fetch MCP tools via MCP protocol" - Protocol error
- "Integrated X MCP tools into system prompt" - Success message

### Server Won't Start

Check the actual error in console output from subprocess

Make sure:
- Python path is correct
- MCP server script exists
- fastmcp is installed
- No syntax errors in server code

### MCP Connection Issues

Verify:
- `mcp` package installed (comes with fastmcp)
- Server process spawned (check ps/Task Manager)
- No firewall blocking stdio pipes

---

**See Also**: [MCP Quick Reference](MCP_TOOLS_QUICK_REF.md), [Settings](settings.yml), [MCP Servers](test_mcp/README.md)

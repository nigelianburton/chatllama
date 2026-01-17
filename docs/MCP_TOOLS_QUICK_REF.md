# MCP Tool Integration - Quick Reference

## How It Works

When ChatLlama starts:

```
1. Build UI
   ↓
2. Check if MCP server running (GET /health)
   ├─ YES → Fetch tools (GET /tools)
   └─ NO  → Launch server → Wait 2 sec → Fetch tools
   ↓
3. Format tools into system prompt
   ↓
4. Model can now suggest using tools
```

## Tool Advertisement Flow

```
MCP Server (/tools endpoint)
  ↓
ChatLlama fetches tools
  ↓
Formats into readable list:
  • tool_name: Description
  • another_tool: Does something useful
  ↓
Adds to system prompt with preamble
  ↓
Model sees tools and can suggest using them
```

## Example System Prompt with Tools

```
You are a helpful assistant.

You have access to specialized tools that extend your capabilities.

Tools Available:
  • create_user_profile: Create a new user profile with favorite style vibes.
  • get_personalized_recommendation: Get a personalized fashion look based on user preferences.
  • save_favorite_look: Save a fashion look to user's favorites.
  • get_user_saved_looks: Get all saved looks for a user.
  • get_user_statistics: Get user statistics and profile information.
  • list_all_looks: List all available fashion looks for 2026.

When a user request requires using a tool, you can suggest using it.
Format: TOOL: [tool_name] with [param1=value1, param2=value2, ...]

Use tools proactively when they would enhance your response to the user.
```

## Configuration (settings.yml)

```yaml
# Enable/disable MCP server
mcp_server_enabled: true

# Where MCP server runs
mcp_server_url: "http://127.0.0.1:8001"

# Include tools in system prompt
tool_integration_enabled: true

# Template for tool preamble
tool_preamble: |
  You have access to specialized tools...
  {tools_list}
```

## MCP Server Requirements

### Health Endpoint
```
GET /health → 200 OK
{
  "status": "healthy",
  "service": "my-service"
}
```

### Tools Endpoint
```
GET /tools → 200 OK
{
  "success": true,
  "tools": [
    {
      "name": "tool_name",
      "description": "What it does",
      "parameters": {
        "param1": "string - description",
        "param2": "int - description"
      }
    }
  ]
}
```

## Code Methods in ChatWindow

### Startup
- `_check_and_launch_mcp_server()` - Called at init, checks and launches server

### Health Check
- `_is_mcp_server_running()` - Checks /health endpoint

### Server Launch
- `_launch_mcp_server()` - Spawns server subprocess with 2-sec startup wait

### Tool Fetching
- `_fetch_mcp_tools()` - Gets tools from /tools endpoint
- `_format_tools_for_prompt()` - Formats as bullet list
- `_fetch_and_integrate_tools()` - Orchestrates fetching and prompt integration

## Example Tool in fashion-curator MCP

```python
@server.tool()
def get_personalized_recommendation(user_id: str) -> dict:
    """Get a personalized fashion look based on user preferences.
    
    Args:
        user_id: The user to get a recommendation for
    
    Returns:
        A personalized fashion look matching user's vibes.
    """
    return curator.get_personalized_look(user_id)
```

This automatically gets advertised in the `/tools` endpoint response.

## Typical Usage Flow

1. User: "What fashion look should I try?"
2. Model sees tool `get_personalized_recommendation` in system prompt
3. Model suggests: "I can help! TOOL: get_personalized_recommendation with [user_id=default]"
4. (Future) ChatLlama executes tool and returns result to model
5. Model: "Here's a perfect look for 2026: [result from tool]"

---

**See Also**: [MCP_INTEGRATION.md](MCP_INTEGRATION.md), [settings.yml](settings.yml)

# FastMCP HTTP Server Query Guide

## Overview

FastMCP servers running on HTTP transport expose their available tools/methods through standard REST endpoints. This guide covers how to properly query a FastMCP server to discover available tools.

## Server Details

- **Base URL**: `http://127.0.0.1:6821`
- **Server Name**: `svg-layout-studio`
- **Transport**: HTTP (not stdio)

## Endpoints

FastMCP HTTP servers expose tools via these standard endpoints:

### 1. **GET /tools** (Recommended)
```
GET http://127.0.0.1:6821/tools
```

Returns a JSON object with a `tools` array:
```json
{
  "tools": [
    {
      "name": "create_artboard",
      "description": "CREATE AN ARTBOARD (CANVAS) FIRST STEP...",
      "inputSchema": {
        "type": "object",
        "properties": {
          "orientation": {
            "type": "string",
            "enum": ["portrait", "landscape"]
          }
        }
      }
    },
    {
      "name": "render_svg",
      "description": "RENDER SVG DESIGN TO DISPLAY...",
      "inputSchema": {
        "type": "object",
        "properties": {
          "artboard_guid": { "type": "string" },
          "svg": { "type": "string" }
        }
      }
    }
  ]
}
```

### 2. **GET /tools/list** (Alternative)
```
GET http://127.0.0.1:6821/tools/list
```

Returns the same format as `/tools`.

### 3. **POST /call_tool** or **POST /tools/call** (Tool Execution)
```
POST http://127.0.0.1:6821/call_tool
Content-Type: application/json

{
  "name": "create_artboard",
  "arguments": {
    "orientation": "portrait"
  }
}
```

Response:
```json
{
  "artboard_guid": "550e8400-e29b-41d4-a716-446655440000",
  "width": 1000,
  "height": 1400,
  "orientation": "portrait",
  "viewBox": "0 0 1000 1400",
  "rules": { ... }
}
```

## Python Code Examples

### Example 1: Simple Tool Discovery

```python
import requests

def discover_fastmcp_tools(base_url: str) -> dict:
    """Query a FastMCP HTTP server to discover available tools."""
    
    # Try both common endpoints
    for endpoint in ("/tools", "/tools/list"):
        try:
            url = base_url.rstrip("/") + endpoint
            response = requests.get(url, timeout=2)
            
            if response.status_code == 200:
                data = response.json()
                tools = data.get("tools", [])
                print(f"✓ Found {len(tools)} tools at {endpoint}")
                return tools
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to query {endpoint}: {e}")
            continue
    
    raise RuntimeError("Could not discover tools from FastMCP server")

# Usage
tools = discover_fastmcp_tools("http://127.0.0.1:6821")
for tool in tools:
    print(f"  • {tool['name']}: {tool['description'][:60]}...")
```

### Example 2: Detailed Tool Inspection

```python
import requests
import json
from typing import List, Dict, Any

def get_fastmcp_tools(base_url: str) -> List[Dict[str, Any]]:
    """Fetch tool definitions from FastMCP HTTP server."""
    
    url = base_url.rstrip("/") + "/tools"
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    
    return response.json()["tools"]

def print_tool_info(tool: Dict[str, Any]) -> None:
    """Pretty-print a tool's details."""
    
    print(f"\n📋 Tool: {tool['name']}")
    print(f"   Description: {tool['description']}")
    
    if "inputSchema" in tool:
        schema = tool["inputSchema"]
        if "properties" in schema:
            print(f"   Parameters:")
            for param_name, param_info in schema["properties"].items():
                param_type = param_info.get("type", "unknown")
                param_desc = param_info.get("description", "")
                print(f"     • {param_name} ({param_type}): {param_desc}")

# Usage
tools = get_fastmcp_tools("http://127.0.0.1:6821")
for tool in tools:
    print_tool_info(tool)
```

### Example 3: Tool Execution with Response Handling

```python
import requests
from typing import Dict, Any, Optional

def execute_fastmcp_tool(
    base_url: str,
    tool_name: str,
    arguments: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Execute a tool on the FastMCP HTTP server."""
    
    # Try primary endpoint first
    for endpoint in ("/call_tool", "/tools/call"):
        try:
            url = base_url.rstrip("/") + endpoint
            response = requests.post(
                url,
                json={"name": tool_name, "arguments": arguments},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
                
        except Exception as e:
            print(f"Endpoint {endpoint} failed: {e}")
            continue
    
    return None

# Usage
result = execute_fastmcp_tool(
    "http://127.0.0.1:6821",
    "create_artboard",
    {"orientation": "landscape"}
)

if result:
    print(f"✓ Created artboard: {result['artboard_guid']}")
    print(f"  Dimensions: {result['width']}x{result['height']}")
else:
    print("✗ Tool execution failed")
```

### Example 4: Retry Logic with Exponential Backoff

```python
import requests
import time
from typing import List, Dict, Any

def fetch_fastmcp_tools_with_retry(
    base_url: str,
    max_retries: int = 5,
    initial_delay: float = 0.5
) -> List[Dict[str, Any]]:
    """Fetch tools with retry logic for unreliable connections."""
    
    url = base_url.rstrip("/") + "/tools"
    retry_delay = initial_delay
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=2)
            
            if response.status_code == 200:
                tools = response.json().get("tools", [])
                print(f"✓ Fetched {len(tools)} tools")
                return tools
            
            print(f"✗ Server returned {response.status_code}")
            
        except requests.exceptions.RequestException as e:
            print(f"✗ Attempt {attempt + 1}/{max_retries} failed: {e}")
        
        if attempt < max_retries - 1:
            print(f"  Retrying in {retry_delay}s...")
            time.sleep(retry_delay)
            retry_delay *= 1.5  # Exponential backoff
    
    raise RuntimeError(f"Failed to fetch tools after {max_retries} attempts")

# Usage
try:
    tools = fetch_fastmcp_tools_with_retry("http://127.0.0.1:6821")
except RuntimeError as e:
    print(f"Error: {e}")
```

### Example 5: Async Approach with httpx

```python
import httpx
import asyncio
from typing import List, Dict, Any

async def get_fastmcp_tools_async(base_url: str) -> List[Dict[str, Any]]:
    """Async version using httpx client."""
    
    async with httpx.AsyncClient(timeout=5) as client:
        url = base_url.rstrip("/") + "/tools"
        response = await client.get(url)
        response.raise_for_status()
        
        return response.json()["tools"]

async def discover_and_execute():
    """Discover tools and execute one."""
    
    # Get tools
    tools = await get_fastmcp_tools_async("http://127.0.0.1:6821")
    print(f"Found {len(tools)} tools")
    
    # Execute a tool
    async with httpx.AsyncClient(timeout=10) as client:
        result = await client.post(
            "http://127.0.0.1:6821/call_tool",
            json={
                "name": "create_artboard",
                "arguments": {"orientation": "portrait"}
            }
        )
        result.raise_for_status()
        
        artboard = result.json()
        print(f"Created artboard: {artboard['artboard_guid']}")

# Usage
asyncio.run(discover_and_execute())
```

## MCP Protocol Details

### Tool Definition Format

Each tool in the response follows the MCP ToolDescription format:

```typescript
interface ToolDescription {
  name: string;                    // Unique tool identifier
  description: string;             // Human-readable description
  inputSchema: JSONSchema;         // JSON Schema for parameters
}
```

### Input Schema Examples

**Simple string parameter:**
```json
{
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "User's name"
    }
  },
  "required": ["name"]
}
```

**Enum selection:**
```json
{
  "type": "object",
  "properties": {
    "size": {
      "type": "string",
      "enum": ["small", "medium", "large"],
      "description": "Item size"
    }
  }
}
```

**Nested object:**
```json
{
  "type": "object",
  "properties": {
    "config": {
      "type": "object",
      "properties": {
        "timeout": {"type": "integer"},
        "retries": {"type": "integer"}
      }
    }
  }
}
```

## Testing the Server

### Using curl

```bash
# Discover tools
curl http://127.0.0.1:6821/tools

# Or alternative endpoint
curl http://127.0.0.1:6821/tools/list

# Execute a tool
curl -X POST http://127.0.0.1:6821/call_tool \
  -H "Content-Type: application/json" \
  -d '{"name": "create_artboard", "arguments": {"orientation": "portrait"}}'
```

### Using Python requests

```python
import requests

# Test connection
response = requests.get("http://127.0.0.1:6821/tools", timeout=2)
print(f"Status: {response.status_code}")
print(f"Tools: {response.json()}")
```

## Error Handling

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Connection refused | Server not running | Start the FastMCP server |
| 404 Not Found | Wrong endpoint | Use `/tools` or `/tools/list` |
| 500 Internal Error | Server crash | Check server logs |
| Timeout | Server busy | Increase timeout, add retry logic |
| Invalid JSON | Malformed request | Validate request format |

### Robust Error Handler

```python
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

def safe_fastmcp_query(base_url: str) -> dict:
    """Query FastMCP with comprehensive error handling."""
    
    try:
        url = base_url.rstrip("/") + "/tools"
        response = requests.get(url, timeout=5)
        
        # Check for HTTP errors
        if response.status_code == 404:
            raise ValueError("Tools endpoint not found (/tools)")
        elif response.status_code == 500:
            raise RuntimeError("Server internal error")
        elif not response.ok:
            raise RuntimeError(f"HTTP {response.status_code}: {response.text}")
        
        # Parse and validate response
        data = response.json()
        tools = data.get("tools", [])
        
        if not isinstance(tools, list):
            raise ValueError("Invalid response format: 'tools' is not a list")
        
        return {"status": "ok", "tools": tools}
        
    except ConnectionError as e:
        return {"status": "error", "message": f"Cannot connect to server: {e}"}
    except Timeout as e:
        return {"status": "error", "message": f"Request timeout: {e}"}
    except ValueError as e:
        return {"status": "error", "message": f"Invalid response: {e}"}
    except RequestException as e:
        return {"status": "error", "message": f"Request failed: {e}"}

# Usage
result = safe_fastmcp_query("http://127.0.0.1:6821")
if result["status"] == "ok":
    print(f"Found {len(result['tools'])} tools")
else:
    print(f"Error: {result['message']}")
```

## Integration Example: ChatLlama Implementation

Based on your ChatLlama codebase, here's how to properly integrate FastMCP HTTP server querying:

```python
# From chatllama_subpanel_mcpinfo.py (your implementation)

def fetch_mcp_tools(self) -> List[Dict[str, Any]]:
    """Fetch tools from HTTP MCP server with retry logic."""
    
    import requests
    url = self.server.get("url")
    
    max_retries = 5
    retry_delay = 0.5
    last_error = None
    
    for attempt in range(max_retries):
        try:
            # Try both standard endpoints
            for endpoint in ("/tools", "/tools/list"):
                try:
                    full = url.rstrip("/") + endpoint
                    resp = requests.get(full, timeout=2)
                    
                    if resp.ok:
                        data = resp.json()
                        tools = data.get("tools") if isinstance(data, dict) else data
                        
                        if tools:
                            logger.debug(f"Fetched {len(tools)} tools from {url}")
                            return tools
                            
                except Exception as e:
                    last_error = e
                    continue
            
            # Retry with exponential backoff
            if attempt < max_retries - 1:
                logger.debug(
                    f"MCP fetch attempt {attempt + 1}/{max_retries} failed, "
                    f"retrying in {retry_delay}s"
                )
                import time
                time.sleep(retry_delay)
                retry_delay *= 1.5
                
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                import time
                time.sleep(retry_delay)
                retry_delay *= 1.5
    
    raise RuntimeError(
        f"HTTP MCP tools fetch failed after {max_retries} attempts: {last_error}"
    )
```

## Summary

- **Endpoint**: `GET http://127.0.0.1:6821/tools` or `/tools/list`
- **Response Format**: `{"tools": [...]}`  with MCP ToolDescription objects
- **Tool Execution**: `POST http://127.0.0.1:6821/call_tool` with `{"name": "...", "arguments": {...}}`
- **Parameter Format**: JSON objects matching the tool's `inputSchema`
- **Best Practice**: Implement retry logic with exponential backoff for reliability

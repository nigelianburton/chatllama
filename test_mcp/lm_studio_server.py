"""MCP Server for querying LM Studio API

This allows the local model to delegate complex queries to LM Studio's
more capable models for reasoning, analysis, or generation tasks.
"""
import logging
from typing import Any
import requests
from mcp.server import Server
from mcp.types import TextContent, Tool
import mcp.server.stdio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lm-studio-mcp")

server = Server("lm-studio-query")

# LM Studio API configuration (OpenAI-compatible)
# Default port is 1234, but can vary (e.g., 11013 for multi-instance)
LM_STUDIO_API_URL = "http://127.0.0.1:11013/v1"
LM_STUDIO_CHAT_ENDPOINT = f"{LM_STUDIO_API_URL}/chat/completions"


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available LM Studio query tools"""
    return [
        Tool(
            name="query_lm_studio",
            description=(
                "Query LM Studio's more capable model for complex reasoning, "
                "analysis, code generation, or detailed explanations. "
                "Use this when you need enhanced capabilities beyond your base model."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The query or task to send to LM Studio's model"
                    },
                    "system_message": {
                        "type": "string",
                        "description": "Optional system message to guide the response",
                        "default": "You are a helpful AI assistant."
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens in response",
                        "default": 2000
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Sampling temperature (0.0 to 2.0)",
                        "default": 0.7
                    }
                },
                "required": ["prompt"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Execute tool calls"""
    
    if name == "query_lm_studio":
        prompt = arguments.get("prompt", "")
        system_message = arguments.get("system_message", "You are a helpful AI assistant.")
        max_tokens = arguments.get("max_tokens", 2000)
        temperature = arguments.get("temperature", 0.7)
        
        if not prompt:
            return [TextContent(type="text", text="Error: No prompt provided")]
        
        try:
            # Make request to LM Studio API
            response = requests.post(
                LM_STUDIO_CHAT_ENDPOINT,
                json={
                    "messages": [
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "stream": False
                },
                timeout=120  # 2 minute timeout for complex queries
            )
            
            if response.status_code == 200:
                data = response.json()
                assistant_message = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                
                result = f"{assistant_message}\n\n[Tokens: {usage.get('total_tokens', 'N/A')}]"
                return [TextContent(type="text", text=result)]
            else:
                error_msg = f"LM Studio API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return [TextContent(type="text", text=f"Error: {error_msg}")]
                
        except requests.exceptions.ConnectionError:
            return [TextContent(
                type="text",
                text="Error: Cannot connect to LM Studio API at http://127.0.0.1:11013. "
                     "Please ensure LM Studio is running with a model loaded and API server is enabled."
            )]
        except requests.exceptions.Timeout:
            return [TextContent(
                type="text",
                text="Error: LM Studio query timed out after 2 minutes."
            )]
        except Exception as e:
            logger.exception("Unexpected error querying LM Studio")
            return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    """Run the MCP server using stdio transport"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

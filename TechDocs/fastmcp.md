Building MCP Servers with .NET: From Development to Publication
Published on July 17, 2025
•
1,558 views
The Model Context Protocol (MCP) is an open standard that enables AI assistants to securely connect to external data sources and tools. Think of it as a bridge between AI models and the real world — letting assistants access databases, APIs, file systems, and custom business logic.

With the release of .NET 10, Microsoft has added native support for creating MCP servers right out of the box. And here's the exciting part — you can now publish your servers to NuGet, making them discoverable by the entire .NET community!

What is MCP and Why Do You Need It?
MCP is often described as "the USB-C port for AI," providing a uniform way to connect LLMs to resources they can use. Simply put, it's like an API, but specifically designed for LLM interactions.

MCP servers can:

Expose data through Resources (think of these like GET endpoints — they're used to load information into the LLM's context)
Provide functionality through Tools (similar to POST endpoints — used to execute code or produce side effects)
Define interaction patterns through Prompts (reusable templates for LLM interactions)
Quick Start: Creating Your First MCP Server
Install the Template
First, let's install the MCP Server template:

dotnet new install Microsoft.Extensions.AI.Templates
Create Your Project
Create a new MCP server using the template:

dotnet new mcpserver -n MyCoolMcpServer
cd MyCoolMcpServer
dotnet build
The template gives you a working MCP server with a sample get_random_number tool. But let's make it more interesting!

Adding Custom Tools
Let's create a new WeatherTools.cs class in the Tools directory:

[McpServerTool]
[Description("Describes random weather in the provided city.")]
public string GetCityWeather(
    [Description("Name of the city to return weather for")] string city)
{
    var weather = Environment.GetEnvironmentVariable("WEATHER_CHOICES");
    if (string.IsNullOrWhiteSpace(weather))
    {
        weather = "sunny,rainy,stormy,foggy";
    }
    
    var weatherChoices = weather.Split(",");
    var selectedWeatherIndex = Random.Shared.Next(0, weatherChoices.Length);
    return $"The weather in {city} is {weatherChoices[selectedWeatherIndex]}.";
}
Now update your Program.cs by adding .WithTools<WeatherTools>() after the previous WithTools call.

Testing with GitHub Copilot
Configure GitHub Copilot to use your MCP server by creating .vscode/mcp.json:

{
  "servers": {
    "MyCoolMcpServer": {
      "type": "stdio",
      "command": "dotnet",
      "args": ["run", "--project", "."],
      "env": {
        "WEATHER_CHOICES": "sunny,humid,freezing,perfect"
      }
    }
  }
}
Now test it with prompts like:

"What's the weather in Seattle?"
"Give me a random number between 1 and 100"
===============
The FastMCP Client

Copy page

Programmatic client for interacting with MCP servers through a well-typed, Pythonic interface.

New in version
2.0.0
The central piece of MCP client applications is the fastmcp.Client class. This class provides a programmatic interface for interacting with any Model Context Protocol (MCP) server, handling protocol details and connection management automatically.
The FastMCP Client is designed for deterministic, controlled interactions rather than autonomous behavior, making it ideal for:
Testing MCP servers during development
Building deterministic applications that need reliable MCP interactions
Creating the foundation for agentic or LLM-based clients with structured, type-safe operations
All client operations require using the async with context manager for proper connection lifecycle management.
This is not an agentic client - it requires explicit function calls and provides direct control over all MCP operations. Use it as a building block for higher-level systems.
​
Creating a Client
Creating a client is straightforward. You provide a server source and the client automatically infers the appropriate transport mechanism.
import asyncio
from fastmcp import Client, FastMCP

# In-memory server (ideal for testing)
server = FastMCP("TestServer")
client = Client(server)

# HTTP server
client = Client("https://example.com/mcp")

# Local Python script
client = Client("my_mcp_server.py")

async def main():
    async with client:
        # Basic server interaction
        await client.ping()
        
        # List available operations
        tools = await client.list_tools()
        resources = await client.list_resources()
        prompts = await client.list_prompts()
        
        # Execute operations
        result = await client.call_tool("example_tool", {"param": "value"})
        print(result)

asyncio.run(main())
​
Client-Transport Architecture
The FastMCP Client separates concerns between protocol and connection:
Client: Handles MCP protocol operations (tools, resources, prompts) and manages callbacks
Transport: Establishes and maintains the connection (WebSockets, HTTP, Stdio, in-memory)
​
Transport Inference
The client automatically infers the appropriate transport based on the input:
FastMCP instance → In-memory transport (perfect for testing)
File path ending in .py → Python Stdio transport
File path ending in .js → Node.js Stdio transport
URL starting with http:// or https:// → HTTP transport
MCPConfig dictionary → Multi-server client
from fastmcp import Client, FastMCP

# Examples of transport inference
client_memory = Client(FastMCP("TestServer"))
client_script = Client("./server.py") 
client_http = Client("https://api.example.com/mcp")
For testing and development, always prefer the in-memory transport by passing a FastMCP server directly to the client. This eliminates network complexity and separate processes.
​
Configuration-Based Clients
New in version
2.4.0
Create clients from MCP configuration dictionaries, which can include multiple servers. While there is no official standard for MCP configuration format, FastMCP follows established conventions used by tools like Claude Desktop.
​
Configuration Format
config = {
    "mcpServers": {
        "server_name": {
            # Remote HTTP/SSE server
            "transport": "http",  # or "sse" 
            "url": "https://api.example.com/mcp",
            "headers": {"Authorization": "Bearer token"},
            "auth": "oauth"  # or bearer token string
        },
        "local_server": {
            # Local stdio server
            "transport": "stdio",
            "command": "python",
            "args": ["./server.py", "--verbose"],
            "env": {"DEBUG": "true"},
            "cwd": "/path/to/server",
        }
    }
}
​
Multi-Server Example
config = {
    "mcpServers": {
        "weather": {"url": "https://weather-api.example.com/mcp"},
        "assistant": {"command": "python", "args": ["./assistant_server.py"]}
    }
}

client = Client(config)

async with client:
    # Tools are prefixed with server names
    weather_data = await client.call_tool("weather_get_forecast", {"city": "London"})
    response = await client.call_tool("assistant_answer_question", {"question": "What's the capital of France?"})
    
    # Resources use prefixed URIs
    icons = await client.read_resource("weather://weather/icons/sunny")
    templates = await client.read_resource("resource://assistant/templates/list")
​
Connection Lifecycle
The client operates asynchronously and uses context managers for connection management:
async def example():
    client = Client("my_mcp_server.py")
    
    # Connection established here
    async with client:
        print(f"Connected: {client.is_connected()}")
        
        # Make multiple calls within the same session
        tools = await client.list_tools()
        result = await client.call_tool("greet", {"name": "World"})
        
    # Connection closed automatically here
    print(f"Connected: {client.is_connected()}")
​
Operations
FastMCP clients can interact with several types of server components:
​
Tools
Tools are server-side functions that the client can execute with arguments.
async with client:
    # List available tools
    tools = await client.list_tools()
    
    # Execute a tool
    result = await client.call_tool("multiply", {"a": 5, "b": 3})
    print(result.data)  # 15
See Tools for detailed documentation.
​
Resources
Resources are data sources that the client can read, either static or templated.
async with client:
    # List available resources
    resources = await client.list_resources()
    
    # Read a resource
    content = await client.read_resource("file:///config/settings.json")
    print(content[0].text)
See Resources for detailed documentation.
​
Prompts
Prompts are reusable message templates that can accept arguments.
async with client:
    # List available prompts
    prompts = await client.list_prompts()
    
    # Get a rendered prompt
    messages = await client.get_prompt("analyze_data", {"data": [1, 2, 3]})
    print(messages.messages)
See Prompts for detailed documentation.
​
Server Connectivity
Use ping() to verify the server is reachable:
async with client:
    await client.ping()
    print("Server is reachable")
​
Initialization and Server Information
When you enter the client context manager, the client automatically performs an MCP initialization handshake with the server. This handshake exchanges capabilities, server metadata, and instructions. The result is available through the initialize_result property.
from fastmcp import Client, FastMCP

mcp = FastMCP(name="MyServer", instructions="Use the greet tool to say hello!")

@mcp.tool
def greet(name: str) -> str:
    """Greet a user by name."""
    return f"Hello, {name}!"

async with Client(mcp) as client:
    # Initialization already happened automatically
    print(f"Server: {client.initialize_result.serverInfo.name}")
    print(f"Version: {client.initialize_result.serverInfo.version}")
    print(f"Instructions: {client.initialize_result.instructions}")
    print(f"Capabilities: {client.initialize_result.capabilities.tools}")
​
Manual Initialization Control
In advanced scenarios, you might want precise control over when initialization happens. For example, you may need custom error handling, want to defer initialization until after other setup, or need to measure initialization timing separately.
Disable automatic initialization and call initialize() manually:
from fastmcp import Client

# Disable automatic initialization
client = Client("my_mcp_server.py", auto_initialize=False)

async with client:
    # Connection established, but not initialized yet
    print(f"Connected: {client.is_connected()}")
    print(f"Initialized: {client.initialize_result is not None}")  # False

    # Initialize manually with custom timeout
    result = await client.initialize(timeout=10.0)
    print(f"Server: {result.serverInfo.name}")

    # Now ready for operations
    tools = await client.list_tools()
The initialize() method is idempotent - calling it multiple times returns the cached result from the first successful call.
​
Client Configuration
Clients can be configured with additional handlers and settings for specialized use cases.
​
Callback Handlers
The client supports several callback handlers for advanced server interactions:
from fastmcp import Client
from fastmcp.client.logging import LogMessage

async def log_handler(message: LogMessage):
    print(f"Server log: {message.data}")

async def progress_handler(progress: float, total: float | None, message: str | None):
    print(f"Progress: {progress}/{total} - {message}")

async def sampling_handler(messages, params, context):
    # Integrate with your LLM service here
    return "Generated response"

client = Client(
    "my_mcp_server.py",
    log_handler=log_handler,
    progress_handler=progress_handler,
    sampling_handler=sampling_handler,
    timeout=30.0
)
The Client constructor accepts several configuration options:
transport: Transport instance or source for automatic inference
log_handler: Handle server log messages
progress_handler: Monitor long-running operations
sampling_handler: Respond to server LLM requests
roots: Provide local context to servers
timeout: Default timeout for requests (in seconds)
​
Transport Configuration
For detailed transport configuration (headers, authentication, environment variables), see the Transports documentation.
​
Next Steps
Explore the detailed documentation for each operation type:
​
Core Operations
Tools - Execute server-side functions and handle results
Resources - Access static and templated resources
Prompts - Work with message templates and argument serialization
​
Advanced Features
Logging - Handle server log messages
Progress - Monitor long-running operations
Sampling - Respond to server LLM requests
Roots - Provide local context to servers
​
Connection Details
Transports - Configure connection methods and parameters
Authentication - Set up OAuth and bearer token authentication
The FastMCP Client is designed as a foundational tool. Use it directly for deterministic operations, or build higher-level agentic systems on top of its reliable, type-safe interface.

====================
Client Transports

Copy page

Configure how FastMCP Clients connect to and communicate with servers.

New in version
2.0.0
The FastMCP Client communicates with MCP servers through transport objects that handle the underlying connection mechanics. While the client can automatically select a transport based on what you pass to it, instantiating transports explicitly gives you full control over configuration—environment variables, authentication, session management, and more.
Think of transports as configurable adapters between your client code and MCP servers. Each transport type handles a different communication pattern: subprocesses with pipes, HTTP connections, or direct in-memory calls.
​
Choosing the Right Transport
Use STDIO Transport when you need to run local MCP servers with full control over their environment and lifecycle
Use Remote Transports when connecting to production services or shared MCP servers running independently
Use In-Memory Transport for testing FastMCP servers without subprocess or network overhead
Use MCP JSON Configuration when you need to connect to multiple servers defined in configuration files
​
STDIO Transport
STDIO (Standard Input/Output) transport communicates with MCP servers through subprocess pipes. This is the standard mechanism used by desktop clients like Claude Desktop and is the primary way to run local MCP servers.
​
The Client Runs the Server
Critical Concept: When using STDIO transport, your client actually launches and manages the server process. This is fundamentally different from network transports where you connect to an already-running server. Understanding this relationship is key to using STDIO effectively.
With STDIO transport, your client:
Starts the server as a subprocess when you connect
Manages the server’s lifecycle (start, stop, restart)
Controls the server’s environment and configuration
Communicates through stdin/stdout pipes
This architecture enables powerful local integrations but requires understanding environment isolation and process management.
​
Environment Isolation
STDIO servers run in isolated environments by default. This is a security feature enforced by the MCP protocol to prevent accidental exposure of sensitive data.
When your client launches an MCP server:
The server does NOT inherit your shell’s environment variables
API keys, paths, and other configuration must be explicitly passed
The working directory and system paths may differ from your shell
To pass environment variables to your server, use the env parameter:
from fastmcp import Client

# If your server needs environment variables (like API keys),
# you must explicitly pass them:
client = Client(
    "my_server.py",
    env={"API_KEY": "secret", "DEBUG": "true"}
)

# This won't work - the server runs in isolation:
# export API_KEY="secret"  # in your shell
# client = Client("my_server.py")  # server can't see API_KEY
​
Basic Usage
To use STDIO transport, you create a transport instance with the command and arguments needed to run your server:
from fastmcp.client.transports import StdioTransport

transport = StdioTransport(
    command="python",
    args=["my_server.py"]
)
client = Client(transport)
You can configure additional settings like environment variables, working directory, or command arguments:
transport = StdioTransport(
    command="python",
    args=["my_server.py", "--verbose"],
    env={"LOG_LEVEL": "DEBUG"},
    cwd="/path/to/server"
)
client = Client(transport)
For convenience, the client can also infer STDIO transport from file paths, but this doesn’t allow configuration:
from fastmcp import Client

client = Client("my_server.py")  # Limited - no configuration options
​
Environment Variables
Since STDIO servers don’t inherit your environment, you need strategies for passing configuration. Here are two common approaches:
Selective forwarding passes only the variables your server actually needs:
import os
from fastmcp.client.transports import StdioTransport

required_vars = ["API_KEY", "DATABASE_URL", "REDIS_HOST"]
env = {
    var: os.environ[var] 
    for var in required_vars 
    if var in os.environ
}

transport = StdioTransport(
    command="python",
    args=["server.py"],
    env=env
)
client = Client(transport)
Loading from .env files keeps configuration separate from code:
from dotenv import dotenv_values
from fastmcp.client.transports import StdioTransport

env = dotenv_values(".env")
transport = StdioTransport(
    command="python",
    args=["server.py"],
    env=env
)
client = Client(transport)
​
Session Persistence
STDIO transports maintain sessions across multiple client contexts by default (keep_alive=True). This improves performance by reusing the same subprocess for multiple connections, but can be controlled when you need isolation.
By default, the subprocess persists between connections:
from fastmcp.client.transports import StdioTransport

transport = StdioTransport(
    command="python",
    args=["server.py"]
)
client = Client(transport)

async def efficient_multiple_operations():
    async with client:
        await client.ping()
    
    async with client:  # Reuses the same subprocess
        await client.call_tool("process_data", {"file": "data.csv"})
For complete isolation between connections, disable session persistence:
transport = StdioTransport(
    command="python",
    args=["server.py"],
    keep_alive=False
)
client = Client(transport)
Use keep_alive=False when you need complete isolation (e.g., in test suites) or when server state could cause issues between connections.
​
Specialized STDIO Transports
FastMCP provides convenience transports that are thin wrappers around StdioTransport with pre-configured commands:
PythonStdioTransport - Uses python command for .py files
NodeStdioTransport - Uses node command for .js files
UvStdioTransport - Uses uv for Python packages (uses env_vars parameter)
UvxStdioTransport - Uses uvx for Python packages (uses env_vars parameter)
NpxStdioTransport - Uses npx for Node packages (uses env_vars parameter)
For most use cases, instantiate StdioTransport directly with your desired command. These specialized transports are primarily useful for client inference shortcuts.
​
Remote Transports
Remote transports connect to MCP servers running as web services. This is a fundamentally different model from STDIO transports—instead of your client launching and managing a server process, you connect to an already-running service that manages its own environment and lifecycle.
​
Streamable HTTP Transport
New in version
2.3.0
Streamable HTTP is the recommended transport for production deployments, providing efficient bidirectional streaming over HTTP connections.
Class: StreamableHttpTransport
Server compatibility: FastMCP servers running with mcp run --transport http
The transport requires a URL and optionally supports custom headers for authentication and configuration:
from fastmcp.client.transports import StreamableHttpTransport

# Basic connection
transport = StreamableHttpTransport(url="https://api.example.com/mcp")
client = Client(transport)

# With custom headers for authentication
transport = StreamableHttpTransport(
    url="https://api.example.com/mcp",
    headers={
        "Authorization": "Bearer your-token-here",
        "X-Custom-Header": "value"
    }
)
client = Client(transport)
For convenience, FastMCP also provides authentication helpers:
from fastmcp.client.auth import BearerAuth

client = Client(
    "https://api.example.com/mcp",
    auth=BearerAuth("your-token-here")
)
​
SSE Transport (Legacy)
Server-Sent Events transport is maintained for backward compatibility but is superseded by Streamable HTTP for new deployments.
Class: SSETransport
Server compatibility: FastMCP servers running with mcp run --transport sse
SSE transport supports the same configuration options as Streamable HTTP:
from fastmcp.client.transports import SSETransport

transport = SSETransport(
    url="https://api.example.com/sse",
    headers={"Authorization": "Bearer token"}
)
client = Client(transport)
Use Streamable HTTP for new deployments unless you have specific infrastructure requirements for SSE.
​
In-Memory Transport
In-memory transport connects directly to a FastMCP server instance within the same Python process. This eliminates both subprocess management and network overhead, making it ideal for testing and development.
Class: FastMCPTransport
Unlike STDIO transports, in-memory servers have full access to your Python process’s environment. They share the same memory space and environment variables as your client code—no isolation or explicit environment passing required.
from fastmcp import FastMCP, Client
import os

mcp = FastMCP("TestServer")

@mcp.tool
def greet(name: str) -> str:
    prefix = os.environ.get("GREETING_PREFIX", "Hello")
    return f"{prefix}, {name}!"

client = Client(mcp)

async with client:
    result = await client.call_tool("greet", {"name": "World"})
​
MCP JSON Configuration Transport
New in version
2.4.0
This transport supports the emerging MCP JSON configuration standard for defining multiple servers:
Class: MCPConfigTransport
config = {
    "mcpServers": {
        "weather": {
            "url": "https://weather.example.com/mcp",
            "transport": "http"
        },
        "assistant": {
            "command": "python",
            "args": ["./assistant.py"],
            "env": {"LOG_LEVEL": "INFO"}
        }
    }
}

client = Client(config)

async with client:
    # Tools are namespaced by server
    weather = await client.call_tool("weather_get_forecast", {"city": "NYC"})
    answer = await client.call_tool("assistant_ask", {"question": "What?"})
​
Tool Transformation with FastMCP and MCPConfig
FastMCP supports basic tool transformations to be defined alongside the MCP Servers in the MCPConfig file.
config = {
    "mcpServers": {
        "weather": {
            "url": "https://weather.example.com/mcp",
            "transport": "http",
            "tools": { }   #  <--- This is the tool transformation section
        }
    }
}
With these transformations, you can transform (change) the name, title, description, tags, enablement, and arguments of a tool.
For each argument the tool takes, you can transform (change) the name, description, default, visibility, whether it’s required, and you can provide example values.
In the following example, we’re transforming the weather_get_forecast tool to only retrieve the weather for Miami and hiding the city argument from the client.
tool_transformations = {
    "weather_get_forecast": {
        "name": "miami_weather",
        "description": "Get the weather for Miami",
        "arguments": {
            "city": {
                "name": "city",
                "default": "Miami",
                "hide": True,
            }
        }
    }
}

config = {
    "mcpServers": {
        "weather": {
            "url": "https://weather.example.com/mcp",
            "transport": "http",
            "tools": tool_transformations
        }
    }
}
​
Allowlisting and Blocklisting Tools
Tools can be allowlisted or blocklisted from the client by applying tags to the tools on the server. In the following example, we’re allowlisting only tools marked with the forecast tag, all other tools will be unavailable to the client.
tool_transformations = {
    "weather_get_forecast": {
        "enabled": True,
        "tags": ["forecast"]
    }
}


config = {
    "mcpServers": {
        "weather": {
            "url": "https://weather.example.com/mcp",
            "transport": "http",
            "tools": tool_transformations,
            "include_tags": ["forecast"]
        }
    }
}
================

Streamable HTTP Transport
New in version
2.3.0
Streamable HTTP is the recommended transport for production deployments, providing efficient bidirectional streaming over HTTP connections.
Class: StreamableHttpTransport
Server compatibility: FastMCP servers running with mcp run --transport http
The transport requires a URL and optionally supports custom headers for authentication and configuration:
from fastmcp.client.transports import StreamableHttpTransport

# Basic connection
transport = StreamableHttpTransport(url="https://api.example.com/mcp")
client = Client(transport)

# With custom headers for authentication
transport = StreamableHttpTransport(
    url="https://api.example.com/mcp",
    headers={
        "Authorization": "Bearer your-token-here",
        "X-Custom-Header": "value"
    }
)
client = Client(transport)
For convenience, FastMCP also provides authentication helpers:
from fastmcp.client.auth import BearerAuth

client = Client(
    "https://api.example.com/mcp",
    auth=BearerAuth("your-token-here")
)
​
SSE Transport (Legacy)
Server-Sent Events transport is maintained for backward compatibility but is superseded by Streamable HTTP for new deployments.
Class: SSETransport
Server compatibility: FastMCP servers running with mcp run --transport sse
SSE transport supports the same configuration options as Streamable HTTP:
from fastmcp.client.transports import SSETransport

transport = SSETransport(
    url="https://api.example.com/sse",
    headers={"Authorization": "Bearer token"}
)
client = Client(transport)
Use Streamable HTTP for new deployments unless you have specific infrastructure requirements for SSE.
​
In-Memory Transport
In-memory transport connects directly to a FastMCP server instance within the same Python process. This eliminates both subprocess management and network overhead, making it ideal for testing and development.
Class: FastMCPTransport
Unlike STDIO transports, in-memory servers have full access to your Python process’s environment. They share the same memory space and environment variables as your client code—no isolation or explicit environment passing required.
from fastmcp import FastMCP, Client
import os

mcp = FastMCP("TestServer")

@mcp.tool
def greet(name: str) -> str:
    prefix = os.environ.get("GREETING_PREFIX", "Hello")
    return f"{prefix}, {name}!"

client = Client(mcp)

async with client:
    result = await client.call_tool("greet", {"name": "World"})
​
MCP JSON Configuration Transport
New in version
2.4.0
This transport supports the emerging MCP JSON configuration standard for defining multiple servers:
Class: MCPConfigTransport
config = {
    "mcpServers": {
        "weather": {
            "url": "https://weather.example.com/mcp",
            "transport": "http"
        },
        "assistant": {
            "command": "python",
            "args": ["./assistant.py"],
            "env": {"LOG_LEVEL": "INFO"}
        }
    }
}

client = Client(config)

async with client:
    # Tools are namespaced by server
    weather = await client.call_tool("weather_get_forecast", {"city": "NYC"})
    answer = await client.call_tool("assistant_ask", {"question": "What?"})
​
Tool Transformation with FastMCP and MCPConfig
FastMCP supports basic tool transformations to be defined alongside the MCP Servers in the MCPConfig file.
config = {
    "mcpServers": {
        "weather": {
            "url": "https://weather.example.com/mcp",
            "transport": "http",
            "tools": { }   #  <--- This is the tool transformation section
        }
    }
}
With these transformations, you can transform (change) the name, title, description, tags, enablement, and arguments of a tool.
For each argument the tool takes, you can transform (change) the name, description, default, visibility, whether it’s required, and you can provide example values.
In the following example, we’re transforming the weather_get_forecast tool to only retrieve the weather for Miami and hiding the city argument from the client.
tool_transformations = {
    "weather_get_forecast": {
        "name": "miami_weather",
        "description": "Get the weather for Miami",
        "arguments": {
            "city": {
                "name": "city",
                "default": "Miami",
                "hide": True,
            }
        }
    }
}

config = {
    "mcpServers": {
        "weather": {
            "url": "https://weather.example.com/mcp",
            "transport": "http",
            "tools": tool_transformations
        }
    }
}
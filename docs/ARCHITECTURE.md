# ChatLlama Architecture

## Overview
ChatLlama is a PyQt6-based desktop application for local LLM inference with MCP (Model Context Protocol) agent capabilities.

## Core Components

### 1. UI Layer (PyQt6 Widgets)
- **SettingsPanel**: Model selection, context configuration, status display
- **ChatPanel**: Conversation history viewer and message input
- **CardsPanel**: Future expansion area for agent cards and tool results

### 2. Model Layer
- **Model Discovery**: Scans `D:\LLM Models\{author}\{model-name}-GGUF` for GGUF files
- **Capabilities Caching**: Reads GGUF metadata (vision, tools, context, VRAM) and caches in `settings.yml`
- **Model Loading**: Uses llama-cpp-python with automatic fallback to llama-server for unsupported models
- **Token Management**: Tracks usage via response stats, displays in status bar, prunes conversation history

### 3. MCP Layer (Agent Tools)
- **MCP Client**: stdio transport for spawning and communicating with MCP servers
- **Tool Discovery**: Fetches tools via MCP `tools/list` protocol
- **Tool Integration**: Injects tool definitions into system prompt
- **Tool Execution**: Detects `TOOL: [name]` pattern in model output, executes via MCP, injects result

### 4. Configuration
- **settings.yml**: User configuration (paths, defaults, model overrides, capabilities cache)
- **mcp.json**: MCP server definitions (currently unused, servers specified in settings.yml)
- **copilot-instructions.md**: AI assistant guidance for development

## Data Flow

```
User Input (ChatPanel)
    ↓
Message Queue → _messages list
    ↓
ChatWorker (QThread) → Non-blocking
    ↓
llama-cpp-python.create_chat_completion(stream=True)
    ↓
Response Chunks → chunk_ready signal → UI Update
    ↓
Tool Detection? → Execute via MCP → Inject result
    ↓
Complete Response → Add to _messages → Display in history
    ↓
Token Usage Stats → Status Bar
```

## Thread Safety
- **Main Thread**: UI rendering, event handling
- **Worker Thread**: Model inference (ChatWorker in QThread)
- **Communication**: Qt signals/slots for cross-thread messaging
- **No Shared State**: Each worker gets immutable copy of message history

## Key Features

### Capability Detection
Automatically scans GGUF metadata for:
- Vision support (mmproj files)
- Tool calling support (specific model architectures)
- Context length (from metadata)
- VRAM usage (measured on first load)

Results cached in `settings.yml` for fast startup.

### Tool Calling (MCP)
1. MCP server spawned on demand via stdio
2. Tools discovered and formatted into system prompt
3. Model outputs `TOOL: get_fashion_look` (example)
4. App parses request, calls MCP `call_tool`
5. Result injected as assistant message
6. Conversation continues

### Context Management
- Configurable per-model context limits (UI spinbox)
- Automatic pruning when conversation exceeds limit
- Keeps system message + last 20 user/assistant pairs

### Automation Mode
- `--input-file` flag for scripted testing
- Processes messages from file sequentially
- Exits cleanly on `EXIT` marker
- All output logged to session logs

## Error Handling
- **Model Loading**: Fallback to llama-server if native load fails
- **Context Overflow**: Automatic pruning with logging
- **Tool Execution**: Graceful failure, continues conversation
- **Automation**: Logs errors and exits cleanly (no hanging)

## File Structure

```
chatllama/
├── src/
│   └── chat.py              # Main application (1800+ lines)
├── config/
│   └── settings.yml         # User configuration + cache
├── docs/
│   ├── ARCHITECTURE.md      # This file
│   ├── MCP_INTEGRATION.md
│   ├── MCP_TOOLS_QUICK_REF.md
│   └── ...
├── tests/
│   ├── test_input.txt
│   └── test_mcp_simple.txt
├── test_mcp/
│   ├── fashion_stdio.py     # Example MCP server
│   └── fashion_server/
├── logs/                    # Session logs
└── chatllama.py            # Launcher
```

## Future Improvements

### Code Organization (In Progress)
- Extract panel widgets to `src/widgets/`
- Extract utilities to `src/utils/` (model_discovery, capabilities, mcp_client)
- Reduce chat.py to <500 lines

### Features
- Native tool calling formats (Qwen JSON, Nemotron render_extra_keys)
- Agent mode toggle (show/hide tool execution)
- Persistent chat history (save/load conversations)
- Multiple MCP servers simultaneously
- Performance profiling and optimization

### Testing
- Unit tests for model discovery
- Integration tests for MCP protocol
- UI tests with pytest-qt
- CI/CD with GitHub Actions

## Dependencies

**Core**:
- PyQt6: Desktop UI framework
- llama-cpp-python: Local LLM inference
- fastmcp: MCP protocol implementation
- gguf: GGUF metadata reading

**Optional**:
- gputil: GPU VRAM monitoring
- numpy: Numerical operations

## Development Environment

**Python**: 3.11.14 (conda environment)
**OS**: Windows (with UTF-8 console support)
**IDE**: VS Code with Python/Pylance
**Backend**: LM Studio's llama.cpp v1.103.2

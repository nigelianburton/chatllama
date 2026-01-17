# ChatLlama - Copilot Instructions

ChatLlama is a PyQt6-based chat interface for local LLMs with agent/MCP support.

## Project Goals
- Lightweight local chat interface using llama-cpp-python
- No LM Studio dependency (works standalone with llama.cpp backend)
- Agent support via Model Context Protocol (MCP) with fastmcp
- Vision model support (Qwen3-VL series)
- Multi-model support with quick switching

## Architecture

### Core Components
- **src/chat.py**: Main PyQt6 application with refactored UI panels
  - **SettingsPanel**: Model selection, context length, GPU offload, load button
  - **ChatPanel**: Message history and input field
  - **CardsPanel**: Cards display (placeholder for future expansion)
- **Models**: GGUF models stored in `D:\LLM Models\{author}\{model-name}-GGUF`
- **Backend**: llama-cpp-python for inference, configured to use LM Studio's llama.cpp v1.103.2
- **MCP Servers**: Test servers in `test_mcp/` for tool discovery and execution
- **Configuration**: `pyproject.toml` (modern Python project), `settings.yml` (app settings)
- **Documentation**: `docs/ARCHITECTURE.md` for detailed system design

### Data Flow
1. User types message → added to message history
2. Message sent to model on worker thread (non-blocking UI)
3. Stream chunks received and displayed in real-time
4. Token usage tracked from llama-cpp-python response
5. Full response added to message list after completion
6. GPU stats updated every second (VRAM, utilization) in status bar
7. MCP tools can be invoked via "TOOL: [name]" in model output

## Development Status

### Completed ✅
- [x] PyQt6 UI with collapsible settings panel
- [x] Model discovery from nested author folders
- [x] llama-cpp-python integration with streaming
- [x] Logging to console and file (chatllama.log)
- [x] Non-blocking chat on worker threads
- [x] Status indicators and error handling
- [x] llama-server fallback for vision models
- [x] fastmcp client installation
- [x] MCP server implementation (fashion-curator, fashion-advisor)
- [x] Proper MCP protocol tool discovery (via decorators)
- [x] Settings configuration file (settings.yml)
- [x] Tool advertisement in system prompt
- [x] Keyboard shortcuts (Enter to send, Ctrl+Enter for newline)
- [x] Command-line automation mode for testing
- [x] GPU monitoring with rolling average (VRAM, utilization)
- [x] Token usage tracking from llama-cpp-python responses
- [x] Status bar showing GPU stats and token counts
- [x] UTF-8 console support for emoji icons on Windows
- [x] Model UI improvements (👁️ vision icon, 🔧 tools icon, maker labels)
- [x] Panel widget refactoring (SettingsPanel, ChatPanel, CardsPanel)
- [x] Modern Python project structure (pyproject.toml, .python-version)
- [x] Development tooling (black, ruff, mypy, pytest)
- [x] Comprehensive architecture documentation (docs/ARCHITECTURE.md)

### TODO 📋

#### Current Work: MCP Tool Integration & Execution

**Issue**: MCP stdio TaskGroup error prevents tools/list from returning; tools still not injected
- Import path fixed (uses stdio_client + StdioServerParameters)
- Tool execution pipeline implemented (parse TOOL:, call MCP, stream result), but blocked by fetch failure
- Need to surface inner TaskGroup exception and make fetch reliable

**Priority Tasks** (in order, test before continuing):
1. [x] **Fix MCP Client Import** - Updated StdioClientTransport to use stdio_client() + StdioServerParameters (current MCP API)
2. [x] **Improve Error Handling** - Log errors and exit gracefully in automation mode (context limit, OOM, etc.) - COMPLETED
3. [ ] **Fix MCP Async Error** - TaskGroup error when calling tools/list via stdio; need to capture inner stack and resolve
4. [x] **Implement Tool Execution** - Parse model "TOOL: [name]" output, execute via MCP, feed results back
5. [ ] **Native Tool Format Support** - Format tools for model-specific calling (Qwen JSON, Nemotron render_extra_keys, etc.)

#### Future Work
- [ ] Agent mode toggle
  - UI switch to enable/disable agent reasoning
  - Show tool calls and results in chat
- [ ] Persistent chat history
  - Save/load conversation threads
  - Export conversations
- [ ] Multi-turn conversation memory management
  - Context window optimization
  - Token counting and pruning
- [ ] Performance optimization
  - Batch inference
  - Caching
- [ ] Additional MCP servers
  - Web search tool
  - Code execution tool
  - File system access

## Building & Running

### Prerequisites
```powershell
conda create -n chatllama python=3.11.14
conda activate chatllama
pip install -r requirements.txt

# Development tools (optional)
pip install -r requirements-dev.txt
```

### Run
```powershell
conda activate chatllama
python src/chat.py
```

### Automation Mode (Testing)
Run with sample input file for automated testing:
```powershell
conda activate chatllama
python src/chat.py --input-file tests/test_input.txt
```

The input file format:
- Each line is a message to send to the model
- Lines starting with `#` are comments and skipped
- Empty lines are ignored
- Use `EXIT`, `#EXIT`, `QUIT`, or `#QUIT` on a line to trigger automatic app shutdown after LLM responds
- All interactions are logged to `logs/session_YYYY-MM-DD_HH-MM-SS.log` for verification

Example `test_input.txt`:
```
# Test messages for automation
Hello, what is Python?
Explain machine learning briefly
EXIT
```

## Configuration

All settings are in `settings.yml`. Key configurations:
- Model paths and defaults
- GPU offload layers and context size
- MCP server enable/command
- Tool integration settings (disabled by default for clean chat)

**Clean Chat Mode (Default):**
- `tool_integration_enabled: false` - Prevents small models from role-playing tool usage
- Models respond naturally like LM Studio without announcing tools
- Enable only for capable models (>= 8B parameters with tool support)

**LM Studio Integration:**
- Use `test_mcp/lm_studio_server.py` to delegate complex queries to LM Studio
- Requires LM Studio running with API enabled (http://localhost:1234)
- Small local models can query more capable LM Studio models for reasoning

See `config/settings.yml.template` for all available options.

## MCP Integration

### Architecture
- **MCP Protocol**: Using standard MCP stdio transport
- **Tool Discovery**: `@server.tool()` decorators expose tools via `tools/list`
- **Tool Advertising**: Formatted into system prompt for model awareness
- **Tool Execution**: Parse model "TOOL: [name]" output, execute via MCP, feed results back

### Test MCP Servers
- `test_mcp/lm_studio_server.py` - Query LM Studio API (delegate complex tasks)
- `test_mcp/fashion_server/` - Stateful server with user profiles (6 tools)
- `test_mcp/fashion_stdio.py` - Stateless server (3 tools)

See `test_mcp/README.md` for details.

## Code Organization

**Key Files:**
- `src/chat.py` - Main application (1800+ lines)
- `pyproject.toml` - Project config with dependencies
- `settings.yml` - Runtime configuration
- `docs/ARCHITECTURE.md` - Comprehensive system documentation
- `tests/` - Test files and automation inputs
- `test_mcp/` - MCP server implementations

## Key Implementation Details

### Panel Widget Architecture
- Three main UI panels as separate widget classes:
  - **SettingsPanel**: Model selection, context/GPU controls (signals: `model_load_requested`, `model_selection_changed`, `ctx_changed`)
  - **ChatPanel**: Message history and input (signal: `send_requested`, methods: `append_to_history()`, `set_input_text()`)
  - **CardsPanel**: Placeholder for future expansion
- Property accessors maintain backwards compatibility with existing code
- Benefits: Better organization, testability, maintainability

### Non-blocking Chat
- `ChatWorker` class extends QObject
- Runs in QThread to avoid freezing UI
- Emits signals for chunk updates
- Proper thread cleanup on completion

### GPU Monitoring
- Rolling 10-sample average for smooth display
- Updated every second via QTimer
- Shows VRAM usage and utilization percentage
- Token counts (prompt + completion) from llama-cpp-python responses
- UTF-8 console wrapper for Windows emoji support

### Model Discovery
- Recursively scans `D:\LLM Models\{author}\` directories
- Filters for GGUF files
- Excludes mmproj (vision projections) files
- Returns relative paths for combo box
- Capability detection: vision (👁️ icon), tools (🔧 icon), maker labels

### Fallback Chain
1. Try llama-cpp-python native loading
2. If error (e.g., unsupported model), check llama-server
3. If not running, auto-launch on port 8000
4. Retry with llama-server

### MCP Client
- Spawns server process with stdio pipes
- Creates async session using `ClientSession`
- Calls standard MCP `tools/list` endpoint
- Formats tools into system prompt

## Known Issues & Solutions

### Vision Models
- Qwen3-VL fails with current llama-cpp-python
- **Solution**: Auto-fallback to llama-server (implemented)

### Tools Not Appearing
- Check `tool_integration_enabled: true` in settings.yml
- Verify MCP server is running
- Check logs: `chatllama.log`

## Code Style

- Type hints on all functions
- Logging at DEBUG/INFO/ERROR levels
- Qt signals/slots for async operations
- Worker threads for long operations
- PEP 8 compliance
- Comments for complex logic
- **Always verify syntax**: Run `python -m py_compile src/chat.py` after editing Python files to catch syntax errors before finishing

## Resources

- [llama-cpp-python](https://github.com/abetlen/llama-cpp-python)
- [FastMCP](https://modelcontextprotocol.io/)
- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [PyQt6](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [GGUF Format](https://github.com/ggerganov/ggml/blob/master/docs/gguf.md)

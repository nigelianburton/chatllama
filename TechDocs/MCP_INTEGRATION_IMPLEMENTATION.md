# MCP integration implementation mapping

## Architecture mapping (plan → implementation)

| Plan component | Current implementation | Notes |
| --- | --- | --- |
| ToolRegistry | SIMPLE/tools/tool_registry.py (`ToolRegistry`, `ToolDefinition`) | Registry populated from fashion_stdio (stdio) on startup. |
| ToolProtocolAdapter | SIMPLE/tools/tool_protocol_base.py + adapters | Implemented adapters: default, qwen, huihui, gemma. |
| ResponseParser | Adapter `parse_tool_calls()` + LlamaCppChatServer `_detect_tool_calls()` | Parses tool calls and triggers execution. |
| ToolExecutor | SIMPLE/tools/tool_executor.py (`ToolExecutor`) | Executes MCP tool calls via stdio for fashion_stdio. |
| MCPClientManager | SIMPLE/tools/mcp_client_manager.py (`MCPClientManager`) | Stdio client for fashion_stdio test server. |
| ContextManager | Not implemented | Needed for tool-result summarization + context budget. |
| llamacpp-server.py transport | LlamaCppChatServer | Loads fashion_stdio tools, injects tool schema, executes tool calls, streams follow-up reply. |

## MCP lifecycle protocol (LLM ↔ ChatLlama ↔ MCP / Display driver)

| LLM | ChatLlama server | MCP / Display driver |
| --- | --- | --- |
| Receives tool schema injection (system prompt or template-defined block) | `ToolProtocolAdapter.render_tools()` prepares tool schema text | External: `FastMCP` server; Internal: card driver API (SVG, future cards) |
| Emits tool call in template-specific format | `_detect_tool_calls()` uses adapter `parse_tool_calls()` | External: awaits tool execution; Internal: UI tool call maps to card updates |
| Awaits tool result message | `ToolExecutor.execute()` → result formatted by adapter | External: `fastmcp.Client.call_tool()`; Internal: UI update and result payload |
| Receives tool result block | `ToolProtocolAdapter.format_tool_result()` | External: returns tool result; Internal: returns card summary + id |
| Continues conversation or makes follow-up tool call | Conversation loop handles additional tool calls | External: can chain calls; Internal: card updates may trigger next step |

## Progress summary

### Built
- Tool protocol adapters for Qwen, Huihui, Gemma, and default parsing.
- Tool registry and executor wired to fashion_stdio (stdio) via MCPClientManager.
- LlamaCppChatServer detects tool calls, executes fashion_stdio tools, and streams follow-up replies.
- Chat history shows MCP request/response bubbles tied to tool calls.
- Cached chat templates in settings to select adapters.
- MCP stdio + HTTP servers active simultaneously; 2026 (stdio) and 1960s (HTTP) fashion MCPs both validated.

### To build next
- MCPClientManager: HTTP client support + connection pooling.
- ToolRegistry population: internal SVG card tools + external MCP config.
- ContextManager: summarize tool responses; size limits for 12K models.
- Multi-call loop guardrails (depth/time caps, retry logic).
- UI glue: explicit tool state transitions on assistant bubbles and card update confirmations.

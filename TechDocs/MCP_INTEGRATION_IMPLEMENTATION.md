# MCP integration implementation mapping

## Architecture mapping (plan → implementation)

| Plan component | Current implementation | Notes |
| --- | --- | --- |
| ToolRegistry | SIMPLE/tools/tool_registry.py (`ToolRegistry`, `ToolDefinition`) | Registry populated from settings-driven MCP servers; tools now prefixed by server name to avoid collisions. |
| ToolProtocolAdapter | SIMPLE/tools/tool_protocol_base.py + adapters | Implemented adapters: default, qwen, huihui, gemma. |
| ResponseParser | Adapter `parse_tool_calls()` + LlamaCppChatServer `_detect_tool_calls()` | Parses tool calls and triggers execution. |
| ToolExecutor | SIMPLE/tools/tool_executor.py (`ToolExecutor`) | Executes MCP tool calls via per-server managers; supports namespaced tools. |
| MCPClientManager | SIMPLE/tools/mcp_client_manager.py (`MCPClientManager`) | Stdio + HTTP support, timeout on list_tools, JSON-serializable result normalization. |
| ContextManager | Not implemented | Needed for tool-result summarization + context budget. |
| llamacpp-server.py transport | LlamaCppChatServer | Loads MCP tools from settings (stdio + HTTP), injects tool schema, executes tool calls, streams follow-up reply. |

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
- Settings-driven MCP discovery (enabled flags, transport, URL/port, methods) with UI toggles.
- LlamaCppChatServer loads MCP tools from settings, injects tool schema, executes tool calls, and streams follow-up replies.
- MCP tool names are namespaced by server to avoid collisions; executor routes to per-server managers.
- Stdio + HTTP MCP support with timeouts and JSON-serializable tool results.
- Chat history shows MCP request/response bubbles tied to tool calls.
- Cached chat templates in settings to select adapters.

### To build next
- ToolRegistry population: internal SVG card tools + external MCP config expansion beyond MCP_Local.
- ContextManager: summarize tool responses; size limits for 12K models.
- Multi-call loop guardrails (depth/time caps, retry logic).
- UI glue: explicit tool state transitions on assistant bubbles and card update confirmations.
- MCP connection pooling/reuse (optional optimization).

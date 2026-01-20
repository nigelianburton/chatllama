# MCP integration strategy (ChatLlama)

Purpose: define how we advertise tools, detect tool requests, execute tools (including UI cards), and return results to the LLM while keeping context tight.

## Scope and invariants
- External MCPs: real services accessed over FastMCP (stdio or HTTP).
- Internal MCPs: card tools exposed by the built-in server (SVG now, more later).
- Must work with small-context models (≈12K) and large models.
- Tool protocol must follow each model’s `chat_template` rules.

## Tool lifecycle (shared for internal + external)
1) Advertise: Send concise tool schemas and capability tags.
2) Detect: Parse model output to detect tool calls.
3) Execute: Route to MCP client or internal card tool.
4) Return: Serialize tool results in the model’s required format.
5) Continue: Feed results back and allow chained tool calls.

## FastMCP transport implications (from TechDocs/fastmcp.md)
- Use stdio for local servers we manage and can spawn.
- Use HTTP for remote/long-running shared servers.
- SSE transport is legacy and not recommended.
- Client controls server lifecycle for stdio (environment isolation is explicit).
- Prefer explicit config for multiple servers with namespacing.

## Model template analysis (from llama_simple/simple_llama_settings.json)

### Devstral-Small-2-24B-Instruct-2512-Q3_K_L
- Cache lacks `chat_template` (currently only generation params). This means we cannot rely on template-defined tool syntax.
- Protocol impact: use OpenAI-compatible tool call format as a default, but add a model-specific override once template is retrieved.

### Huihui-Ministral-3-8B-Reasoning-2512-abliterated.Q4_K_S
- Template explicitly defines `[AVAILABLE_TOOLS]`, `[TOOL_CALLS]`, and `[TOOL_RESULTS]` sections.
- User messages are wrapped in `[INST]...[/INST]`; images are replaced by `[IMG]` tokens.
- Tool calls are embedded as text with `name[ARGS]{...}` in a `[TOOL_CALLS]` block.
- Protocol impact:
  - Advertise tools via `[AVAILABLE_TOOLS]{json}[/AVAILABLE_TOOLS]`.
  - Parse tool calls inside `[TOOL_CALLS]` block (name + JSON args).
  - Return tool results in `[TOOL_RESULTS]...[/TOOL_RESULTS]`.

### Qwen3-VL-4B-Instruct-abliterated-v2.Q4_K_S
### Qwen3-VL-8B-Instruct-abliterated-v2.0.Q4_K_S
- Tooling uses XML-like tags: `<tools>...</tools>` and `<tool_call>{"name":..., "arguments":...}</tool_call>`.
- User multimodal content emits `<|vision_start|><|image_pad|><|vision_end|>` tokens; actual image bytes are passed via OpenAI `image_url` data URL.
- Protocol impact:
  - Tools must be injected in the system prompt using `<tools>` with JSON tool definitions.
  - Tool calls must be parsed from `<tool_call>` tags.
  - Tool results must be placed in `<tool_response>` blocks (as shown in template).

### Qwen2.5-VL-7B-Abliterated-Caption-it.Q4_K_S
- Similar to Qwen3-VL vision tokens and `<|im_start|>` framing; no explicit tool schema wrapper in template.
- Protocol impact:
  - Use OpenAI tool calling as a fallback, or inject tools as a system message with a short instruction.
  - Keep tool schemas minimal to avoid context blow-up.

### gemma-3-27b-it-abliterated.Q3_K_S
### gemma3-27B-it-abliterated-normpreserve-Q3_K_M
- Template uses `<start_of_turn>` framing; images are `<start_of_image>` tokens.
- No tool schema region or tool call syntax defined.
- Protocol impact:
  - Use a minimal system instruction describing tool call JSON format.
  - Expect tool calls to be plain JSON or a simple tagged block; be permissive in parsing.

### default
- No template: treat as unknown. Use an OpenAI-compatible tool call format with short system prompt.

## Why templates matter
- Tool syntax is not universal. Some models require explicit markers (XML or bracketed tags) and will ignore “generic” tool schemas.
- Vision placeholders are template-driven: you must provide image bytes *and* the correct token markers in text content.
- The adapter must enforce each model’s message framing and tool representation to ensure reliable tool invocation.

## Recommended architecture
Keep `SIMPLE/llamacpp-server.py` focused on transport and server health. Move tool-specific logic into a small, function-oriented module set:

1) ToolRegistry
- Stores tool definitions (name, schema, server, type=external/internal).
- Creates minimal tool lists based on model context budget.

2) ToolProtocolAdapter (per model family)
- `render_tools(tools, system_prompt)`
- `parse_tool_calls(text)`
- `format_tool_result(tool_call_id, payload)`
- Examples: `adapter_huihui.py`, `adapter_qwen.py`, `adapter_gemma.py`, `adapter_default.py`.

3) ToolExecutor
- Routes calls to FastMCP clients (external) or internal card handlers.
- Supports async execution, timeouts, and caching.

4) MCPClientManager
- Owns FastMCP client connections per server (stdio or HTTP).
- Handles start/stop for stdio servers and reconnect policy for HTTP.

5) ContextManager
- Summarizes tool responses and compresses history.
- Inserts pointers (tool_result_id + summary) instead of full payload when needed.

6) ResponseParser
- Converts model output into structured events: text, tool_calls, errors.
- A tolerant parser is critical for small models.

## Context-budget strategy (small models)
- Use abbreviated tool schemas (name + 1–2 sentence description + minimal args).
- Provide a short “tool protocol card” to explain format, not the full spec.
- Allow search tools that accept line ranges and file globbing so the model can request specifics instead of full documents.
- Use IDs for tool results and only inline a short summary; full results are retrievable via follow-up tool calls.
- Keep tool result payloads under a fixed token/char budget; use truncation with “continue” tool.

## Internal cards vs external MCPs
- Internal cards are MCP tools with side effects on UI; treat as `tool` results with a short confirmation (“card updated”) and optional summary.
- External MCPs should return structured JSON or small text summaries; large payloads should be summarized or stored by reference.

## Practical protocol guidance
- Always align with the model’s template: the adapter is mandatory.
- Prefer a single tool call per turn for small models to reduce error rate.
- Keep tool results deterministic; avoid sending long logs back to the model.
- Log tool requests and results for debugging (already implemented).

## Next steps
- Create per-model adapters based on templates above and plug into the chat flow.
- Add a compact “tool protocol” system prompt for models without explicit tool sections.
- Implement a minimal tool discovery MCP for filesystem search, line ranges, and snippet retrieval.
- Add a sandboxed “run small python” MCP with tight resource limits for scripted transformations.

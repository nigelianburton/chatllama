# Tool Integration Fix Plan

## Objective
Adapt ChatLlama to match LM Studio's tool calling protocol exactly. LM Studio successfully uses our MCP tools by:
1. Providing explicit tool format instructions in the system prompt
2. Using `[TOOL_REQUEST]...[END_TOOL_REQUEST]` markers for tool calls
3. Returning tool results in `[TOOL_RESULT]...[END_TOOL_RESULT]` format
4. Feeding results back to the model for response generation

**Current Problem**: ChatLlama passes tools via the `tools` parameter to `create_chat_completion()`, but:
- Gemma outputs text instead of structured tool calls
- We look for "TOOL:" format (which Gemma doesn't produce)
- Tools are never actually executed

**LM Studio Proof**: The attached log shows Gemma successfully calling `get_fashion_look` and the model correctly using the result. We must replicate this exact behavior.

---

## Research Tasks (Must Complete First)

### 1. Understand llama-cpp-python Tool Formatting
**Goal**: Learn exactly how llama-cpp-python formats tools in the prompt

**Tasks**:
- [ ] Enable debug mode in llama-cpp-python to capture the actual rendered prompt with tools
- [ ] Compare rendered prompt to LM Studio's prompt format (see attached log)
- [ ] Identify what's different and why Gemma outputs generic text instead of `[TOOL_REQUEST]` blocks
- [ ] Check if llama-cpp-python's chat_template is the issue

**Location**: Research in `src/chat.py` ChatWorker class

**Deliverable**: Document showing:
- Actual prompt being sent to Gemma with tools parameter
- LM Studio's prompt format (from log)
- Differences identified

---

### 2. Reverse Engineer LM Studio's Tool Prompt Template
**Goal**: Extract the exact system prompt/instructions LM Studio uses

**Tasks**:
- [ ] Examine the LM Studio log to identify the tool instruction format
- [ ] Note the exact markers: `[TOOL_REQUEST]`, `[END_TOOL_REQUEST]`, `[TOOL_RESULT]`, `[END_TOOL_RESULT]`
- [ ] Document the example format with JSON structure
- [ ] Note the "Rules" section provided to the model
- [ ] Identify when tools are shown vs. "No tools available"

**Deliverable**: Text file with the exact tool prompt template to use

---

### 3. Test FastMCP Tool Description Format
**Goal**: Verify what format FastMCP provides tool descriptions in

**Tasks**:
- [ ] Add logging to `_fetch_mcp_tools()` to capture raw MCP ToolDescription objects
- [ ] Convert to OpenAI format and log the JSON
- [ ] Compare structure to what LM Studio shows in the log
- [ ] Verify parameter descriptions are being captured

**Location**: `src/chat.py` line ~1176

**Deliverable**: Log output showing tool descriptions in both MCP format and converted format

---

## Code Changes (Implementation Phase)

### Phase 1: System Prompt - Don't Pass Tools Parameter

**Goal**: Replace the `tools` parameter approach with explicit prompt-based instructions

**Tasks**:
- [ ] **Create new method**: `_build_tool_prompt()` in ChatWindow
  - Input: list of MCP tools (from `_fetch_mcp_tools()`)
  - Output: formatted prompt section matching LM Studio format
  - Must include: tool list in JSON, format instructions, examples, rules

- [ ] **Modify `_start_chat_completion()`**:
  - Remove: `tools=openai_tools` parameter to ChatWorker
  - Add: Inject tool prompt into system message (or as user message preamble)
  - Keep tools in local `self._mcp_tools` for later execution

- [ ] **Update ChatWorker initialization**:
  - Remove: `tools` parameter from `__init__`
  - Remove: `self.tools` instance variable
  - Remove: tools from `completion_kwargs`

**Files to modify**: `src/chat.py` (lines ~291, ~310, ~1914)

**Verification**:
- [ ] Syntax check: `python -m py_compile src/chat.py`
- [ ] Log output should show tool prompt being injected (add logging to `_build_tool_prompt()`)

---

### Phase 2: Tool Call Parsing - Detect `[TOOL_REQUEST]` Blocks

**Goal**: Parse model output for structured tool calls instead of "TOOL:" format

**Tasks**:
- [ ] **Replace `_parse_tool_request()`**:
  - Old: Looks for "TOOL: tool_name with [params]" format
  - New: Parse `[TOOL_REQUEST]...[END_TOOL_REQUEST]` blocks
  - Extract: `{"name": "...", "arguments": {...}}`
  - Handle multiple tool calls in one response

- [ ] **Add regex pattern**:
  ```regex
  \[TOOL_REQUEST\]\s*(\{.*?\})\s*\[END_TOOL_REQUEST\]
  ```
  - Must handle JSON parsing of arguments
  - Must handle multiple calls

- [ ] **Add logging**:
  - Log detected tool requests before execution
  - Log parsed JSON for debugging

**Files to modify**: `src/chat.py` (lines ~1240-1295)

**Verification**:
- [ ] Test with sample JSON: `{"name": "get_fashion_look", "arguments": {}}`
- [ ] Test with parameters: `{"name": "get_look_by_vibe", "arguments": {"vibe": "bold"}}`
- [ ] Test with multiple calls in one message

---

### Phase 3: Tool Execution - Call MCPs and Format Results

**Goal**: Execute detected tool calls and return results in LM Studio format

**Tasks**:
- [ ] **Enhance `_execute_tool_call()`**:
  - Input: `tool_name` (string) and `arguments` (dict)
  - Execute via MCP using `_fetch_mcp_tools()` results
  - Return: Result object or error message

- [ ] **Create new method**: `_format_tool_result()` (already exists, verify it works)
  - Input: MCP CallToolResult
  - Output: JSON string suitable for wrapping in `[TOOL_RESULT]` tags

- [ ] **Modify `_on_chat_finished()`**:
  - After receiving full response from model
  - Parse for `[TOOL_REQUEST]` blocks
  - For each tool found:
    - Execute via MCP
    - Format result in `[TOOL_RESULT]...[END_TOOL_RESULT]` format
    - **Append to conversation**: Add tool result as new user message
    - **Re-run model**: Call `create_chat_completion()` again with updated history
    - Accumulate final response (may have multiple tool calls)

**Files to modify**: `src/chat.py` (lines ~1296-1360, ~1960-2000)

**Verification**:
- [ ] Tool execution returns valid data
- [ ] Results wrapped correctly in tags
- [ ] Model receives results and generates final response

---

### Phase 4: Conversation Loop - Handle Multi-Turn Tool Interactions

**Goal**: Support multiple tool calls in a single conversation turn

**Tasks**:
- [ ] **Create new method**: `_run_model_with_tool_handling()`
  - Runs `create_chat_completion()`
  - Detects tool calls in output
  - Executes tools and formats results
  - Re-runs model with results
  - Returns final response (with tools executed)

- [ ] **Modify `_on_chat_finished()`**:
  - Call new `_run_model_with_tool_handling()` method
  - Handle loop termination (max 5 iterations to prevent infinite loops)
  - Log each iteration

- [ ] **Add safety limits**:
  - Max tool calls per response: 5
  - Max total iterations: 5
  - Timeout: 60 seconds

**Files to modify**: `src/chat.py` (entire chat completion flow)

**Verification**:
- [ ] Single tool call → model response
- [ ] Multiple tool calls in one response → all executed
- [ ] Tool result fed back → model generates final answer
- [ ] Safety limits prevent infinite loops

---

## Testing & Validation

### Test 1: Simple Tool Call
**Query**: "What is a good 2026 fashion look? List only one."
**Expected**:
1. Model outputs `[TOOL_REQUEST]{"name": "get_fashion_look", "arguments": {}}[END_TOOL_REQUEST]`
2. Tool executed, result returned in `[TOOL_RESULT]...[END_TOOL_RESULT]`
3. Model generates final answer using result
4. Log shows: "Tool executed: get_fashion_look", result JSON, final response

**Test File**: `tests/test_tool_call_simple.txt`

---

### Test 2: Tool With Parameters
**Query**: "Show me a bold fashion look for 2026"
**Expected**:
1. Model calls `get_look_by_vibe` with `{"vibe": "bold"}`
2. Tool executes with parameter
3. Result returned and used
4. Final response reflects the specific vibe

**Test File**: `tests/test_tool_call_with_params.txt`

---

### Test 3: No Tools Needed
**Query**: "What is the capital of France?"
**Expected**:
1. Model responds directly (no tool calls)
2. No `[TOOL_REQUEST]` blocks detected
3. Response generated without tool execution

**Test File**: `tests/test_no_tools.txt`

---

### Test 4: Multiple Tool Calls
**Query**: "Show me all available 2026 fashion looks and also show me a bold one"
**Expected**:
1. Model makes multiple tool calls in one response
2. Both executed sequentially
3. Results fed back to model
4. Final response uses both results

**Test File**: `tests/test_multiple_tools.txt`

---

## Logging Requirements

Add logging at each step:

1. **Tool Prompt Building**: 
   ```
   2026-01-18 ... - INFO - Tool prompt: 3 tools available, {tool count} lines
   ```

2. **Tool Request Detection**:
   ```
   2026-01-18 ... - INFO - Tool request detected: get_fashion_look with {}
   ```

3. **Tool Execution**:
   ```
   2026-01-18 ... - INFO - Executing tool: get_fashion_look
   2026-01-18 ... - INFO - Tool result: {JSON}
   ```

4. **Multi-Turn Loop**:
   ```
   2026-01-18 ... - DEBUG - Tool handling iteration 1/5
   2026-01-18 ... - DEBUG - Re-running model with tool results
   ```

5. **Final Response**:
   ```
   2026-01-18 ... - INFO - Final response (after tools): {text}
   ```

---

## Success Criteria

✅ **MVP**: Tool calls detected and executed
- [ ] Model outputs `[TOOL_REQUEST]` blocks
- [ ] Blocks parsed correctly
- [ ] Tools executed via MCP
- [ ] Results returned to model
- [ ] Final response generated

✅ **Full Feature**: Multiple tools in sequence
- [ ] Single response with multiple tool calls → all executed
- [ ] Tool results fed back to model
- [ ] Model uses results in final answer
- [ ] Loop safety limits prevent hangs

✅ **Robustness**: Error handling
- [ ] Invalid tool names → graceful error message
- [ ] Missing parameters → error message
- [ ] MCP connection failures → logged and handled
- [ ] Malformed JSON → parsing error logged

---

## Files to Create/Modify

### New Files
- [ ] `tests/test_tool_call_simple.txt` - Simple tool call test
- [ ] `tests/test_tool_call_with_params.txt` - Tool with parameters
- [ ] `tests/test_no_tools.txt` - Regular query without tools
- [ ] `tests/test_multiple_tools.txt` - Multiple tool calls

### Modified Files
- [ ] `src/chat.py` - Main changes (ChatWindow and ChatWorker)
- [ ] `src/chatllama_cpp.py` - (if needed for MCP execution)

### Documentation
- [ ] This file: `TOOL_PLAN.md`
- [ ] Update `docs/MCP_INTEGRATION.md` with new approach
- [ ] Update architecture docs

---

## Timeline & Milestones

**Phase 1** (Research): 1-2 hours
- Understand current tool formatting
- Document LM Studio approach
- Capture actual prompts

**Phase 2** (Parsing): 1-2 hours  
- Implement `[TOOL_REQUEST]` parsing
- Test with sample JSON
- Verify regex patterns

**Phase 3** (Execution): 2-3 hours
- Enhance tool execution
- Format results correctly
- Test single tool calls

**Phase 4** (Loop): 2-3 hours
- Implement multi-turn tool handling
- Add safety limits
- Comprehensive testing

**Total Estimated**: 6-10 hours

---

## Notes

- **Do NOT deviate** from LM Studio's approach without explicit approval
- **Reference**: LM Studio log shows the exact protocol to follow
- **Key Insight**: Tools are NOT passed via parameter; instead, they're injected as prompt text
- **Next Step**: Start with Research Phase 1 to confirm current behavior

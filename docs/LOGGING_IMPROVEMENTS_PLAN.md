# ChatLlama Logging Improvements Plan

## Executive Summary

Current log files are **51% noise** (1,251 Redis polling lines out of 2,450 total lines). This plan restructures logging to be **concise, navigable, and LLM-friendly** while maintaining full detail where needed.

**Key Metrics from Analysis (session_2026-01-18_20-17-49.log)**:
- Total lines: 2,450
- Redis/fastmcp polling: 1,251 lines (51%)
- Per-chunk streaming: 30 lines (each chunk creates noise)
- Useful program flow: ~1,169 lines (49%)

## Design Principles

1. **LLM First**: Logs should help coding agents understand:
   - What triggered an action
   - What parameters were used
   - What the result was
   - Where to find more detail if needed

2. **Hierarchical Detail**: Use log levels to control verbosity:
   - **ERROR**: Problems requiring attention
   - **WARNING**: Unexpected but handled conditions
   - **INFO**: High-level program flow (user actions, model responses, tool execution)
   - **DEBUG**: Detailed parameters and state (but condensed)
   - **TRACE** (new): Raw protocol traffic (Redis, HTTP, MCP wire protocol)

3. **Signal-to-Noise Optimization**:
   - Consolidate repetitive operations (polling loops → summary)
   - Summarize streams (per-chunk → start/end with stats)
   - Group related operations (tool execution → one block)

4. **Navigability**: Use visual markers:
   - Section headers with `====`
   - Subsection markers with `----`
   - Action markers with `►►►`
   - Result markers with `◄◄◄`

## Problem Categories & Solutions

### 1. Redis/FastMCP Polling Spam (51% of log)

**Current State** (1,251 lines):
```
2026-01-18 20:18:32,262 - DEBUG - Getting redeliveries
2026-01-18 20:18:32,262 - DEBUG - >>> None: [b'XREADGROUP', b'GROUP', b'docket-workers', ...]
2026-01-18 20:18:32,387 - DEBUG - Scheduling due tasks
2026-01-18 20:18:32,387 - DEBUG - >>> None: [b'EVALSHA', '39773dff...', b'2', ...]
(repeats every 250ms for entire session)
```

**Problems**:
- Obscures actual work being done
- Makes searching for issues difficult
- Not useful for debugging unless investigating fastmcp itself

**Solution**: Move to TRACE level + periodic summaries
```
# TRACE level (hidden by default)
2026-01-18 20:18:32,262 - TRACE - [FastMCP] Poll: redeliveries=0, new=0, tasks=0

# INFO level (shown every 30 seconds OR when queue has items)
2026-01-18 20:18:30,000 - INFO - [FastMCP] Active: queue=0, stream=0, workers=1 (last 30s: 120 polls, 0 tasks)

# INFO level (when something happens)
2026-01-18 20:18:45,123 - INFO - [FastMCP] ►►► New task enqueued: id=abc123, type=tool_call
```

**Implementation**:
- Add TRACE log level (below DEBUG)
- Move Redis commands to TRACE
- Add periodic INFO summary with counters
- Log state changes at INFO level

**Savings**: Reduces from 1,251 lines to ~4 lines per session

---

### 2. LLM Streaming Chunks (30 lines per response)

**Current State**:
```
2026-01-18 20:18:27,325 - DEBUG - Chunk #1
2026-01-18 20:18:27,326 - DEBUG - Chunk #2
2026-01-18 20:18:27,432 - DEBUG - Chunk #3
...
2026-01-18 20:18:30,224 - DEBUG - Streaming complete: 30 chunks, 129 total chars
```

**Problems**:
- Hides timing information (time to first token = latency indicator)
- No tokens/second metric
- Chunk count without content not useful

**Solution**: Summary with metrics + optional detail
```
# INFO level (shown always)
2026-01-18 20:18:06,774 - INFO - [LLM] ►►► Starting completion: model=gemma-3n-E4B, messages=2, max_tokens=1024
2026-01-18 20:18:27,325 - INFO - [LLM] First token after 20.55s
2026-01-18 20:18:30,224 - INFO - [LLM] ◄◄◄ Complete: 129 chars (30 chunks) in 23.45s @ 5.5 chars/s
2026-01-18 20:18:30,225 - INFO - [LLM] Response: "The capital of France is Paris. This is a general knowledge question..."

# DEBUG level (optional, shows every 10th chunk + timing)
2026-01-18 20:18:27,325 - DEBUG - [LLM Stream] Chunk 1 (+0.55s): "The"
2026-01-18 20:18:28,432 - DEBUG - [LLM Stream] Chunk 10 (+1.66s): "capital of France is Paris"
2026-01-18 20:18:29,642 - DEBUG - [LLM Stream] Chunk 20 (+2.87s): " question and doesn't"
2026-01-18 20:18:30,224 - DEBUG - [LLM Stream] Chunk 30 (+3.45s, final): " tools."
```

**Implementation**:
- Log start with parameters (INFO)
- Log first token with latency (INFO)
- Log completion with stats (INFO)
- Log final text preview (INFO, truncate at 200 chars)
- Log every 10th chunk at DEBUG

**Savings**: Reduces from 32 lines to 4-5 INFO lines + optional DEBUG detail

---

### 3. UI Initialization Spam (25+ lines)

**Current State**:
```
2026-01-18 20:17:50,187 - INFO - [ChatPanel __init__] START - self=1998712098528
2026-01-18 20:17:50,187 - INFO - [ChatPanel __init__] About to call _build_ui(), self=1998712098528
2026-01-18 20:17:50,196 - INFO - [ChatPanel Init] Created history_widget: widget=<PyQt6...>, id=1998703501248
2026-01-18 20:17:50,197 - INFO - ChatPanel signals connected. Container exists: False
2026-01-18 20:17:50,198 - INFO - [ChatPanel Init] Before addWidget - history_widget: <PyQt6...>
2026-01-18 20:17:50,198 - INFO - [ChatPanel Init] After addWidget - history_widget: <PyQt6...>
...
```

**Problems**:
- Too granular for INFO level
- Widget memory addresses not useful unless debugging crashes
- "Before/After" pattern creates 2x logs

**Solution**: One line per component + parameters at DEBUG
```
# INFO level (shown always)
2026-01-18 20:17:50,187 - INFO - [UI] Initializing ChatPanel (history + input + send button)
2026-01-18 20:17:50,223 - INFO - [UI] Initializing CardsPanel (CardChrome for SVG display)
2026-01-18 20:17:50,228 - INFO - [UI] Model discovery: scanning D:\LLM Models

# DEBUG level (optional details)
2026-01-18 20:17:50,196 - DEBUG - [ChatPanel] history_widget created: QListWidget@1998703501248
2026-01-18 20:17:50,200 - DEBUG - [CardChrome] QSvgWidget: size=400×300, minHeight=200
```

**Implementation**:
- Move step-by-step init logs to DEBUG
- Use single INFO line per major component
- Only log widget addresses at DEBUG
- Remove "Before/After" pattern (just log result)

**Savings**: Reduces from 25+ lines to 3-4 INFO lines

---

### 4. Tool Execution Flow (Scattered across 20+ lines)

**Current State**:
```
2026-01-18 20:11:42,550 - DEBUG - Found TOOL_REQUEST JSON: create_artboard with 28 chars args
2026-01-18 20:11:42,550 - INFO - TOOL REQUEST DETECTED: create_artboard
2026-01-18 20:11:42,550 - DEBUG - Tool call parsed: create_artboard with args...
2026-01-18 20:11:42,551 - DEBUG - Attempting built-in tool execution: create_artboard
2026-01-18 20:11:42,551 - INFO - Calling built-in MCP HTTP server for tool: create_artboard
2026-01-18 20:11:42,551 - DEBUG - HTTP MCP request: POST http://localhost:6821/call_tool
2026-01-18 20:11:42,651 - INFO - Tool 'create_artboard' executed successfully via HTTP MCP
2026-01-18 20:11:42,652 - INFO - Tool result: {"status": "success", "artboard_guid": "932245..."}
```

**Problems**:
- 8+ lines for one tool call
- Multiple redundant "detected/parsed/calling" logs
- Result logged separately from execution

**Solution**: Consolidate into action block with visual markers
```
# INFO level (shown always)
2026-01-18 20:11:42,550 - INFO - ═══════════════════════════════════════════════════════════════
2026-01-18 20:11:42,550 - INFO - [TOOL] ►►► Executing: create_artboard (via HTTP MCP :6821)
2026-01-18 20:11:42,550 - INFO - [TOOL]     Arguments: {"orientation": "landscape"}
2026-01-18 20:11:42,651 - INFO - [TOOL] ◄◄◄ Success in 101ms
2026-01-18 20:11:42,651 - INFO - [TOOL]     Result: {"status": "success", "artboard_guid": "93224561..."}
2026-01-18 20:11:42,651 - INFO - ═══════════════════════════════════════════════════════════════

# DEBUG level (optional wire-level detail)
2026-01-18 20:11:42,550 - DEBUG - [TOOL] Raw request: POST http://localhost:6821/call_tool
2026-01-18 20:11:42,551 - DEBUG - [TOOL] Request body: {"name": "create_artboard", "arguments": {...}}
2026-01-18 20:11:42,651 - DEBUG - [TOOL] Response: 200 OK, 156 bytes
```

**Implementation**:
- Create tool execution context manager to wrap logging
- Use visual markers (═══ for blocks, ►►► for start, ◄◄◄ for results)
- Consolidate all tool info into one block
- Move HTTP details to DEBUG

**Savings**: Reduces from 8+ lines to 5 INFO lines (one clear block)

---

### 5. Model Loading Verbose Steps (15+ lines)

**Current State**:
```
2026-01-18 20:17:55,123 - DEBUG - Loading model: mradermacher\gemma-3n-E4B...
2026-01-18 20:17:55,124 - DEBUG - Model path: D:\LLM Models\mradermacher\gemma-3n-E4B...
2026-01-18 20:17:55,124 - DEBUG - Context size: 8192
2026-01-18 20:17:55,125 - DEBUG - GPU layers: 99
2026-01-18 20:17:55,125 - DEBUG - Temperature: 0.7
2026-01-18 20:17:57,456 - INFO - Model loaded successfully in 2.33s
```

**Problems**:
- Each parameter gets its own line
- No clear start/end markers
- Missing VRAM usage information

**Solution**: Compact parameter block + timing + metrics
```
# INFO level (shown always)
2026-01-18 20:17:55,123 - INFO - ═══════════════════════════════════════════════════════════════
2026-01-18 20:17:55,123 - INFO - [MODEL] ►►► Loading: gemma-3n-E4B-it-abliterated-i1-Q4_K_S.gguf
2026-01-18 20:17:55,124 - INFO - [MODEL]     Context: 8192 | GPU Layers: 99 | Temp: 0.7
2026-01-18 20:17:57,456 - INFO - [MODEL] ◄◄◄ Loaded in 2.33s | VRAM: 3.82 GB | Ready
2026-01-18 20:17:57,456 - INFO - ═══════════════════════════════════════════════════════════════

# DEBUG level (optional full path + backend info)
2026-01-18 20:17:55,124 - DEBUG - [MODEL] Path: D:\LLM Models\mradermacher\gemma-3n-E4B...
2026-01-18 20:17:55,125 - DEBUG - [MODEL] Backend: llama-cpp-python 0.2.57 (llama.cpp b1234)
```

**Savings**: Reduces from 15+ lines to 4 INFO lines

---

### 6. MCP Server Connection (Verbose handshake)

**Current State**:
```
2026-01-18 20:17:53,213 - DEBUG - Using proactor: IocpProactor
2026-01-18 20:17:53,213 - INFO - Connecting to MCP server via stdio: python test_mcp/fashion_stdio.py
2026-01-18 20:17:54,742 - INFO - MCP list_tools returned 3 tools
2026-01-18 20:17:54,876 - INFO - Fetched 3 tools from MCP server via MCP protocol
2026-01-18 20:17:54,876 - DEBUG - Converted 3 Tool objects to dict format
2026-01-18 20:17:54,876 - INFO - Final tool list for system prompt: 3 tools
2026-01-18 20:17:54,877 - DEBUG -   1. get_fashion_look - Get a hot woman's fashion trend...
2026-01-18 20:17:54,877 - DEBUG -   2. get_all_looks - Get all hot fashion trends...
2026-01-18 20:17:54,877 - DEBUG -   3. get_look_by_vibe - Get a hot 2026 fashion trend...
```

**Problems**:
- 3 separate logs saying "3 tools" (redundant)
- Tool descriptions repeated in logs (already in system prompt)

**Solution**: Single connection block with tool list
```
# INFO level (shown always)
2026-01-18 20:17:53,213 - INFO - ─────────────────────────────────────────────────────────────
2026-01-18 20:17:53,213 - INFO - [MCP] ►►► Connecting: stdio → python test_mcp/fashion_stdio.py
2026-01-18 20:17:54,876 - INFO - [MCP] ◄◄◄ Connected in 1.66s | Tools: 3
2026-01-18 20:17:54,876 - INFO - [MCP]     • get_fashion_look
2026-01-18 20:17:54,876 - INFO - [MCP]     • get_all_looks
2026-01-18 20:17:54,876 - INFO - [MCP]     • get_look_by_vibe
2026-01-18 20:17:54,877 - INFO - ─────────────────────────────────────────────────────────────

# DEBUG level (optional full tool schemas)
2026-01-18 20:17:54,877 - DEBUG - [MCP Tool] get_fashion_look: Get a hot woman's fashion trend for 2026...
2026-01-18 20:17:54,877 - DEBUG - [MCP Tool]   Parameters: (none)
```

**Savings**: Reduces from 10+ lines to 7 INFO lines (one clear block)

---

## Implementation Strategy

### Phase 1: Add TRACE Level & FastMCP Cleanup
**Files**: `src/chat.py` (logging setup), fastmcp polling code
**Impact**: Eliminates 1,200+ lines of noise
**Effort**: 2 hours

1. Add TRACE level (numeric value 5, below DEBUG=10)
2. Move all Redis operations to TRACE
3. Add periodic INFO summary every 30 seconds
4. Add state change detection (idle → active → idle)

### Phase 2: Streaming Summary
**Files**: `src/chat.py` (ChatWorker._run_chat method)
**Impact**: Reduces streaming from 30+ lines to 5 lines
**Effort**: 1 hour

1. Track timing: time_start, time_first_token, time_end
2. Calculate metrics: total_time, chars/sec, chunks
3. Log only: start → first_token → complete (with metrics)
4. Add DEBUG mode for chunk-by-chunk (every 10th)

### Phase 3: Component Consolidation
**Files**: All `src/chatllama_pane_*.py` files
**Impact**: Reduces init from 25+ lines to 5 lines
**Effort**: 2 hours

1. Remove "Before/After" pattern
2. Move widget addresses to DEBUG
3. Use one INFO line per major component
4. Add section markers for startup phase

### Phase 4: Action Blocks with Visual Markers
**Files**: `src/chat.py` (tool execution, model loading)
**Impact**: Reduces tool calls from 8+ to 5 lines, model load from 15 to 4
**Effort**: 3 hours

1. Create logging context managers:
   - `@log_tool_execution`
   - `@log_model_operation`
   - `@log_mcp_connection`
2. Use visual markers: `═══` (blocks), `───` (sections), `►►►` (start), `◄◄◄` (end)
3. Consolidate parameters into single lines
4. Add timing and metrics

### Phase 5: Searchability & Navigation
**Files**: All Python files with logging
**Impact**: Makes logs grep-friendly
**Effort**: 2 hours

1. Consistent prefixes: `[LLM]`, `[TOOL]`, `[MCP]`, `[UI]`, `[MODEL]`
2. Consistent action markers: `►►►` (start), `◄◄◄` (end/result)
3. Add separator lines for major sections
4. Document grep patterns in README

---

## Expected Results

### Before & After Comparison

**Current (session_2026-01-18_20-17-49.log)**:
- Total lines: 2,450
- Noise: 1,281 lines (52%)
- Signal: 1,169 lines (48%)
- Search difficulty: High (must filter noise)
- LLM context cost: High (includes all noise)

**After Implementation**:
- Total lines: ~400 (84% reduction)
- Noise at INFO: 0 lines (moved to TRACE)
- Signal: 400 lines (100% at INFO)
- Search difficulty: Low (clear markers + prefixes)
- LLM context cost: Low (only relevant logs)

### Grep Patterns for Navigation

```powershell
# Find all tool executions
Get-Content session.log | Select-String "\[TOOL\] ►►►"

# Find all model loading operations
Get-Content session.log | Select-String "\[MODEL\] ►►►"

# Find all LLM completions with timing
Get-Content session.log | Select-String "\[LLM\] ◄◄◄ Complete"

# Find all errors/warnings
Get-Content session.log | Select-String " - (ERROR|WARNING) - "

# Find major section boundaries
Get-Content session.log | Select-String "═══════════════"

# Get execution timeline (start/end markers only)
Get-Content session.log | Select-String "►►►|◄◄◄"
```

---

## Logging Configuration

### New Log Levels
```python
# Add to src/chat.py
import logging

# Define TRACE level (below DEBUG)
TRACE = 5
logging.addLevelName(TRACE, 'TRACE')

def trace(self, message, *args, **kwargs):
    if self.isEnabledFor(TRACE):
        self._log(TRACE, message, args, **kwargs)

logging.Logger.trace = trace
```

### Console vs File Configuration
```python
# Console handler: INFO and above (user-facing)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
)

# File handler: DEBUG and above (for LLM agents)
file_handler = logging.FileHandler(session_log_file)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
)

# Add TRACE file for deep debugging (optional, separate file)
trace_handler = logging.FileHandler(session_trace_file)
trace_handler.setLevel(TRACE)
trace_handler.setFormatter(
    logging.Formatter('%(asctime)s - TRACE - %(message)s')
)
```

### Usage Example
```python
# High-level flow (always visible)
logger.info("[TOOL] ►►► Executing: create_artboard")

# Implementation details (visible in file)
logger.debug("[TOOL] HTTP request: POST http://localhost:6821/call_tool")

# Wire protocol (separate trace file)
logger.trace("[TOOL] Raw response: b'{\"status\":\"success\"...}'")
```

---

## Benefits for LLM Coding Agents

### 1. Faster Context Gathering
- **Before**: Scroll through 2,450 lines, manually filter noise
- **After**: Grep for `[TOOL]` or `►►►` markers, get clean timeline

### 2. Clearer Causality
- **Before**: Action scattered across 8+ lines, hard to trace
- **After**: Action in one block with clear start/end markers

### 3. Better Metrics
- **Before**: "Streaming complete: 30 chunks" (no timing)
- **After**: "Complete: 129 chars in 23.45s @ 5.5 chars/s"

### 4. Issue Isolation
- **Before**: Error buried in 1,200 lines of Redis polling
- **After**: Error clearly visible with context block

### 5. Reduced Token Costs
- **Before**: 2,450 lines × ~50 tokens/line = 122,500 tokens
- **After**: 400 lines × ~50 tokens/line = 20,000 tokens (84% savings)

---

## Success Metrics

1. **Log Size**: Target 60-80% reduction in line count
2. **Signal-to-Noise**: Target >95% signal at INFO level
3. **Search Time**: Target <5 seconds to find any tool/model operation via grep
4. **LLM Context**: Target <25k tokens for typical session log
5. **Debugging Time**: Target 50% reduction in time to isolate issues

---

## Future Enhancements

1. **Structured Logging**: Add JSON mode for machine parsing
2. **Log Aggregation**: Send to centralized logging (ELK, Loki, etc.)
3. **Performance Tracing**: Add OpenTelemetry spans for distributed tracing
4. **Interactive Viewer**: Web UI to filter/search logs by component/level
5. **Automatic Summarization**: LLM-generated session summaries in log footer

---

## Appendix: Reference Implementation

### Tool Execution Context Manager
```python
@contextmanager
def log_tool_execution(tool_name: str, method: str, arguments: dict):
    """Context manager for clean tool execution logging."""
    start_time = time.time()
    logger.info("═" * 63)
    logger.info(f"[TOOL] ►►► Executing: {tool_name} (via {method})")
    logger.info(f"[TOOL]     Arguments: {json.dumps(arguments, indent=None)}")
    
    try:
        yield
        elapsed = time.time() - start_time
        logger.info(f"[TOOL] ◄◄◄ Success in {elapsed*1000:.0f}ms")
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[TOOL] ◄◄◄ Failed in {elapsed*1000:.0f}ms: {e}")
        raise
    finally:
        logger.info("═" * 63)

# Usage
with log_tool_execution("create_artboard", "HTTP MCP :6821", {"orientation": "landscape"}):
    result = await mcp.call_tool("create_artboard", arguments)
    logger.info(f"[TOOL]     Result: {json.dumps(result, indent=None)}")
```

### Streaming Metrics Collector
```python
class StreamingMetrics:
    def __init__(self):
        self.start_time = time.time()
        self.first_token_time = None
        self.chunk_count = 0
        self.total_chars = 0
        self.chunks_logged = []
    
    def add_chunk(self, chunk: str):
        if self.first_token_time is None:
            self.first_token_time = time.time()
            latency = self.first_token_time - self.start_time
            logger.info(f"[LLM] First token after {latency:.2f}s")
        
        self.chunk_count += 1
        self.total_chars += len(chunk)
        
        # Log every 10th chunk at DEBUG
        if self.chunk_count % 10 == 0:
            elapsed = time.time() - self.start_time
            logger.debug(f"[LLM Stream] Chunk {self.chunk_count} (+{elapsed:.2f}s): \"{chunk[:50]}...\"")
    
    def finalize(self, full_text: str):
        end_time = time.time()
        total_time = end_time - self.start_time
        chars_per_sec = self.total_chars / total_time if total_time > 0 else 0
        
        logger.info(f"[LLM] ◄◄◄ Complete: {self.total_chars} chars ({self.chunk_count} chunks) in {total_time:.2f}s @ {chars_per_sec:.1f} chars/s")
        logger.info(f"[LLM] Response: \"{full_text[:200]}{'...' if len(full_text) > 200 else ''}\"")
```

---

## Document History
- 2026-01-18: Initial draft (Copilot analysis of session_2026-01-18_20-17-49.log)

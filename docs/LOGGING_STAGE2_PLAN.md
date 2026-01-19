# ChatLlama Logging Improvements - Stage 2 Plan

## Executive Summary

**Stage 1 Results**: Successfully reduced log file from **2,450 → 565 lines (77% reduction)**

This Stage 2 document identifies remaining noise patterns and plans the next round of improvements.

## Stage 1 Achievements ✅

1. **TRACE Level Infrastructure**: Added below DEBUG for protocol traffic
2. **LLM Streaming Metrics**: Added timing (first token latency, chars/sec, total time)
3. **Visual Markers**: Implemented ►►► / ◄◄◄ for grep-friendly navigation
4. **Component Prefixes**: Added [LLM], [TOOL] for filtering
5. **Tool Execution Blocks**: Added ═══ boundaries with timing

**Visual Markers Working**:
```
2026-01-18 20:33:06,567 - INFO - [LLM] ►►► Starting completion: messages=2
2026-01-18 20:33:18,066 - INFO - [LLM] First token after 11.50s
```

## Remaining Issues (565 lines)

### Issue 1: UI Initialization Spam (25+ lines)

**Current State** (INFO level):
```
2026-01-18 20:32:55,930 - INFO - [ChatPanel __init__] START - self=2020799827680
2026-01-18 20:32:55,931 - INFO - [ChatPanel __init__] About to call _build_ui(), self=2020799827680
2026-01-18 20:32:55,939 - INFO - [ChatPanel Init] Created history_widget: widget=<...>, id=2022922035136, self=2020799827680
2026-01-18 20:32:55,944 - INFO - ChatPanel signals connected. Container exists: False
2026-01-18 20:32:55,944 - INFO - [ChatPanel Init] Before addWidget - history_widget: <...>
2026-01-18 20:32:55,944 - INFO - [ChatPanel Init] After addWidget - history_widget: <...>
2026-01-18 20:32:55,944 - INFO - [ChatPanel Init] Before setLayout - history_widget: <...>
2026-01-18 20:32:55,945 - INFO - [ChatPanel Init] After setLayout - history_widget: <...>
2026-01-18 20:32:55,945 - INFO - [ChatPanel __init__] END - self=2020799827680, history_widget=None
```

**Problem**: 9 INFO lines for widget initialization - too verbose

**Solution**:
```python
# Move detailed UI construction to DEBUG
logger.debug("[ChatPanel Init] Created history_widget: %s", widget_id)
logger.debug("[ChatPanel Init] Added to layout")

# Keep only 1 INFO line
logger.info("[UI] ChatPanel initialized")
```

**Impact**: 25+ → 3-4 lines

---

### Issue 2: Per-Token ChatPanel Updates (100+ lines)

**Current State** (INFO level):
```
2026-01-18 20:33:18,067 - INFO - [ChatPanel Append] Called with message_type=assistant, self=2020799827680, history_widget=<...>
2026-01-18 20:33:18,172 - INFO - [ChatPanel Append] Called with message_type=assistant, self=2020799827680, history_widget=<...>
2026-01-18 20:33:18,285 - INFO - [ChatPanel Append] Called with message_type=assistant, self=2020799827680, history_widget=<...>
... (repeated per token/chunk)
```

**Problem**: Logs every token append to UI - creates 100+ lines per response

**Solution**:
```python
# In ChatPanel.append_to_history():
# Only log at INFO for new messages (not token updates)
if is_new_message:
    logger.info("[UI] Added %s message to history", message_type)
else:
    # Token streaming updates to DEBUG or remove entirely
    logger.debug("[UI] Updated message bubble (token stream)")
```

**Impact**: 100+ → 2-3 lines per response

---

### Issue 3: Card Widget Verbosity (15+ lines)

**Current State** (INFO level):
```
2026-01-18 20:32:55,945 - INFO - Creating CardChrome widget for SVG display
2026-01-18 20:32:55,945 - INFO - [CardChrome] __init__ called with parent: QWidget
2026-01-18 20:32:55,945 - INFO - [CardChrome] After super().__init__, CardBase size: PyQt6.QtCore.QSize(100, 300)
2026-01-18 20:32:55,946 - INFO - [CardChrome] Created QSvgWidget for SVG rendering
2026-01-18 20:32:55,946 - INFO - [CardChrome] QSvgWidget configured. Size: ..., minHeight: 200
... (10 more lines)
```

**Problem**: 15 INFO lines for card initialization

**Solution**:
```python
# Move construction details to DEBUG
logger.debug("[CardChrome] Created QSvgWidget: size=%s", size)

# Keep only 1 INFO line
logger.info("[UI] CardChrome initialized: content loaded")
```

**Impact**: 15+ → 1 line

---

### Issue 4: Tool Definition Spam (12+ lines per completion)

**Current State** (INFO level):
```
2026-01-18 20:33:06,534 - INFO - Tool definition: {
  "type": "function",
  "function": {
    "name": "get_fashion_look",
    "description": "Get a hot woman's fashion trend...",
    "parameters": { ... }
  }
}
... (repeated for 3+ tools)
```

**Problem**: Logs full JSON for each tool definition at INFO - takes 12+ lines

**Solution**:
```python
# Log tool names only at INFO
logger.info("[MCP] Loaded tools: %s", ", ".join(tool_names))

# Full definitions at DEBUG
for tool in tools:
    logger.debug("[MCP] Tool: %s - %s", tool['name'], tool['description'][:50])

# Full JSON at TRACE (optional, for debugging MCP protocol)
logger.trace("[MCP Protocol] Tool definition: %s", json.dumps(tool, indent=2))
```

**Impact**: 12+ → 1 line at INFO (full details at DEBUG)

---

### Issue 5: System Prompt Duplication (50+ lines)

**Current State** (INFO/DEBUG level):
```
2026-01-18 20:33:01,640 - DEBUG - Tool prompt:

## Available Tools
... (30 lines of markdown)

2026-01-18 20:33:06,536 - DEBUG - === SYSTEM MESSAGE FOR THIS COMPLETION ===
You are a helpful assistant.

## Available Tools
... (50+ lines repeated)
```

**Problem**: System prompt logged twice, once at startup and once per completion

**Solution**:
```python
# Log prompt only at DEBUG, and only first X lines
prompt_preview = system_prompt.split('\n')[:5]
logger.debug("[LLM] System prompt: %s... (%d chars)", '\n'.join(prompt_preview), len(system_prompt))

# Full prompt at TRACE (optional, for debugging)
logger.trace("[LLM Protocol] Full system prompt:\n%s", system_prompt)
```

**Impact**: 50+ → 1 line at DEBUG (full at TRACE if needed)

---

### Issue 6: Model Discovery Verbosity (15+ lines)

**Current State** (DEBUG level):
```
2026-01-18 20:32:55,978 - DEBUG - Scanning author folder: DavidAU
2026-01-18 20:32:55,979 - DEBUG - Found model: DavidAU\Qwen3-24B-A4B-Freedom-HQ...
2026-01-18 20:32:55,979 - DEBUG - Scanning author folder: lmstudio-community
... (15+ lines, one per model)
```

**Problem**: Logs every folder scan at DEBUG - verbose at startup

**Solution**:
```python
# Keep at DEBUG but consolidate
logger.debug("[MODEL] Scanning: %s", author_folder)
# ... scan logic ...

# Summary at INFO
logger.info("[MODEL] Discovered %d models in %d folders", model_count, folder_count)
```

**Current Impact**: Already at DEBUG, acceptable. Consider consolidating in Stage 3.

---

## Stage 2 Implementation Strategy

### Phase 1: UI Initialization Cleanup (10 min)
- **Target**: [ChatPanel Init], [CardChrome], [CardBase] logs
- **Action**: Move construction details to DEBUG, keep 1 INFO line per component
- **Expected**: 40+ → 5 lines

### Phase 2: Per-Token Update Elimination (15 min)
- **Target**: [ChatPanel Append] called per token
- **Action**: Add `is_new_message` flag, log only new messages at INFO
- **Expected**: 100+ → 2-3 lines per response

### Phase 3: Tool Definition Consolidation (10 min)
- **Target**: Tool definition JSON spam
- **Action**: Log tool names at INFO, full definitions at DEBUG/TRACE
- **Expected**: 12+ → 1 line per completion

### Phase 4: System Prompt Deduplication (5 min)
- **Target**: Repeated system prompt logging
- **Action**: Log preview at DEBUG, full at TRACE
- **Expected**: 50+ → 1 line at DEBUG

**Total Time**: ~40 minutes  
**Expected Reduction**: 565 → ~250 lines (56% further reduction, **90% total reduction** from 2,450)

---

## Stage 2 Expected Outcome

**Before Stage 2**: 565 lines (77% reduction from 2,450)  
**After Stage 2**: ~250 lines (90% total reduction from 2,450)

**Noise Breakdown**:
- UI initialization: 40+ → 5 lines (-35)
- Per-token updates: 100+ → 3 lines (-97)
- Tool definitions: 12+ → 1 line (-11)
- System prompt: 50+ → 1 line (-49)

**Total Stage 2 Reduction**: ~192 lines (-34%)

**INFO Level Composition** (After Stage 2):
- ✅ 100% signal: Only high-level actions with metrics
- ✅ LLM: Start/first token/completion with timing
- ✅ TOOL: Execution blocks with timing
- ✅ MODEL: Load/unload with VRAM metrics
- ✅ MCP: Connection + tool count summary

**DEBUG Level Composition** (After Stage 2):
- ✅ Implementation details: Widget IDs, sizes, paths
- ✅ Tool definitions: Names + descriptions
- ✅ System prompt preview: First 5 lines
- ✅ Model discovery: Per-folder scan results

**TRACE Level Composition** (After Stage 2):
- ✅ Protocol wire traffic: Full JSON payloads
- ✅ Redis commands: Raw XREADGROUP calls
- ✅ HTTP bodies: Full request/response dumps
- ✅ Full system prompts: Complete text for debugging

---

## Stage 3 Considerations (Future)

After Stage 2 fog clears, consider:

1. **Structured Logging** (JSON mode)
   - Optional `--log-format=json` flag
   - Machine-readable for LLM agent parsing
   - Preserves human-readable default

2. **Log Level Profiles**
   - `--log-level=minimal`: INFO only (user-facing)
   - `--log-level=standard`: INFO + DEBUG (default)
   - `--log-level=verbose`: INFO + DEBUG + TRACE (dev/debugging)

3. **Performance Metrics Summary**
   - End-of-session report: Total tokens, avg latency, VRAM usage
   - Logged at INFO when app exits
   - Single 5-line block replacing scattered stats

4. **Async Logging** (if performance issue)
   - Queue-based logging to avoid UI thread blocking
   - Only implement if latency measured > 5ms

5. **Context Manager Decorators**
   - Implement `@log_action` decorator for automatic ►►► / ◄◄◄ markers
   - Example: `@log_action("TOOL", "get_fashion_look")` wraps method

---

## Grep Patterns (Stage 2)

After Stage 2 improvements, these patterns will be even cleaner:

```bash
# Find all LLM completions (start to end)
grep '\[LLM\] ►►►'

# Find all tool executions
grep '\[TOOL\] ►►►'

# Find all first token latencies (user-perceived delay)
grep 'First token after'

# Find all UI operations
grep '\[UI\]'

# Find all errors/warnings
grep 'ERROR\|WARNING'

# Get session summary (startup + shutdown)
grep '============================================================'
```

**Expected Results**:
- `[LLM] ►►►`: 1-2 hits per completion (fast lookup)
- `[TOOL] ►►►`: 0-5 hits per session (tool executions)
- `[UI]`: 10-15 hits total (startup + message adds)

---

## Validation Criteria (Stage 2)

After Stage 2, run test and verify:

1. ✅ **Line Count**: New log file < 300 lines (target: ~250)
2. ✅ **Grep Speed**: `grep '\[LLM\] ►►►'` returns in < 2 seconds
3. ✅ **INFO Signal**: No UI spam at INFO level (0 "Before/After addWidget")
4. ✅ **Token Updates**: 0 "[ChatPanel Append]" at INFO during streaming
5. ✅ **Tool Definitions**: 0 full JSON tool definitions at INFO
6. ✅ **System Prompt**: 0 full prompt dumps at INFO/DEBUG (only at TRACE)
7. ✅ **Metrics Preserved**: All timing metrics still present (latency, chars/sec)

**Test Command**:
```powershell
# Run short test
python src\chat.py --input-file tests\test_hi.txt

# Analyze new log
$log = (Get-ChildItem logs\session_*.log | Sort LastWriteTime -Desc | Select -First 1).FullName
Write-Host "Total lines: $((Get-Content $log | Measure-Object -Line).Lines)"
Write-Host "UI spam: $((Get-Content $log | Select-String '\[ChatPanel Init\] Before|After').Count)"
Write-Host "Token updates: $((Get-Content $log | Select-String '\[ChatPanel Append\]').Count)"
Write-Host "Tool JSON: $((Get-Content $log | Select-String 'Tool definition:').Count)"
```

---

## Priority Ranking

**Immediate** (Stage 2):
1. Per-token ChatPanel updates (-100 lines) - **HIGHEST IMPACT**
2. System prompt deduplication (-50 lines)
3. UI initialization cleanup (-35 lines)
4. Tool definition consolidation (-11 lines)

**Future** (Stage 3):
1. Structured logging (JSON mode)
2. Log level profiles (minimal/standard/verbose)
3. Session summary report

---

## Summary

Stage 1 achieved **77% reduction** (2,450 → 565 lines). Stage 2 targets remaining UI spam, per-token updates, and tool definition verbosity for **90% total reduction** (2,450 → 250 lines).

**Key Focus**: Eliminate per-token ChatPanel append logs (-100 lines), deduplicate system prompt (-50 lines), and consolidate UI initialization (-35 lines).

**Next Steps**:
1. Implement Phase 1-4 changes (40 minutes)
2. Test with sample input file
3. Validate line count < 300
4. Review for Stage 3 opportunities

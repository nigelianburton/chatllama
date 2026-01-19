# ChatLlama Logging Quick Reference

## Visual Markers

```
═══════════════════════════════════════  Major section boundary (tool, model load)
─────────────────────────────────────  Minor section boundary (MCP connection)
►►►  Action start marker
◄◄◄  Result/completion marker
```

## Component Prefixes

| Prefix | Component | Example |
|--------|-----------|---------|
| `[LLM]` | Model inference | `[LLM] ►►► Starting completion: model=gemma-3n` |
| `[TOOL]` | Tool execution | `[TOOL] ►►► Executing: create_artboard` |
| `[MCP]` | MCP server ops | `[MCP] ►►► Connecting: stdio → fashion_stdio.py` |
| `[MODEL]` | Model loading | `[MODEL] ►►► Loading: gemma-3n-E4B.gguf` |
| `[UI]` | UI components | `[UI] Initializing ChatPanel` |
| `[FastMCP]` | MCP polling | `[FastMCP] Active: queue=0, stream=0` |

## Log Levels

| Level | Numeric | Purpose | File | Console |
|-------|---------|---------|------|---------|
| **TRACE** | 5 | Protocol wire traffic (Redis, HTTP raw) | ✓ (separate) | ✗ |
| **DEBUG** | 10 | Implementation details, parameters | ✓ | ✗ |
| **INFO** | 20 | High-level flow, user actions | ✓ | ✓ |
| **WARNING** | 30 | Unexpected but handled | ✓ | ✓ |
| **ERROR** | 40 | Problems requiring attention | ✓ | ✓ |

## Grep Patterns

### Find all tool executions
```powershell
Get-Content session.log | Select-String "\[TOOL\] ►►►"
```

### Find all model operations
```powershell
Get-Content session.log | Select-String "\[MODEL\] ►►►"
```

### Find all LLM completions with metrics
```powershell
Get-Content session.log | Select-String "\[LLM\] ◄◄◄ Complete"
```

### Get execution timeline (start + end only)
```powershell
Get-Content session.log | Select-String "►►►|◄◄◄"
```

### Find errors and warnings
```powershell
Get-Content session.log | Select-String " - (ERROR|WARNING) - "
```

### Find all section boundaries
```powershell
Get-Content session.log | Select-String "═══════════════|─────────────"
```

### Extract just timestamps and actions
```powershell
Get-Content session.log | Select-String "►►►|◄◄◄" | ForEach-Object { $_ -replace '^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}).*?(►►►|◄◄◄)(.*)$', '$1 $2$3' }
```

## Example: Tool Execution Block

```log
2026-01-18 20:11:42,550 - INFO - ═══════════════════════════════════════════════════════════════
2026-01-18 20:11:42,550 - INFO - [TOOL] ►►► Executing: create_artboard (via HTTP MCP :6821)
2026-01-18 20:11:42,550 - INFO - [TOOL]     Arguments: {"orientation": "landscape"}
2026-01-18 20:11:42,651 - INFO - [TOOL] ◄◄◄ Success in 101ms
2026-01-18 20:11:42,651 - INFO - [TOOL]     Result: {"status": "success", "artboard_guid": "93224561"}
2026-01-18 20:11:42,651 - INFO - ═══════════════════════════════════════════════════════════════
```

## Example: LLM Streaming with Metrics

```log
2026-01-18 20:18:06,774 - INFO - [LLM] ►►► Starting completion: model=gemma-3n-E4B, messages=2, max_tokens=1024
2026-01-18 20:18:27,325 - INFO - [LLM] First token after 20.55s
2026-01-18 20:18:30,224 - INFO - [LLM] ◄◄◄ Complete: 129 chars (30 chunks) in 23.45s @ 5.5 chars/s
2026-01-18 20:18:30,225 - INFO - [LLM] Response: "The capital of France is Paris. This is a general knowledge question..."
```

## Example: Model Loading

```log
2026-01-18 20:17:55,123 - INFO - ═══════════════════════════════════════════════════════════════
2026-01-18 20:17:55,123 - INFO - [MODEL] ►►► Loading: gemma-3n-E4B-it-abliterated-i1-Q4_K_S.gguf
2026-01-18 20:17:55,124 - INFO - [MODEL]     Context: 8192 | GPU Layers: 99 | Temp: 0.7
2026-01-18 20:17:57,456 - INFO - [MODEL] ◄◄◄ Loaded in 2.33s | VRAM: 3.82 GB | Ready
2026-01-18 20:17:57,456 - INFO - ═══════════════════════════════════════════════════════════════
```

## Example: MCP Connection

```log
2026-01-18 20:17:53,213 - INFO - ─────────────────────────────────────────────────────────────
2026-01-18 20:17:53,213 - INFO - [MCP] ►►► Connecting: stdio → python test_mcp/fashion_stdio.py
2026-01-18 20:17:54,876 - INFO - [MCP] ◄◄◄ Connected in 1.66s | Tools: 3
2026-01-18 20:17:54,876 - INFO - [MCP]     • get_fashion_look
2026-01-18 20:17:54,876 - INFO - [MCP]     • get_all_looks
2026-01-18 20:17:54,876 - INFO - [MCP]     • get_look_by_vibe
2026-01-18 20:17:54,877 - INFO - ─────────────────────────────────────────────────────────────
```

## Logging Usage in Code

### High-level flow (INFO)
```python
logger.info("[TOOL] ►►► Executing: create_artboard")
logger.info("[TOOL] ◄◄◄ Success in 101ms")
```

### Implementation details (DEBUG)
```python
logger.debug("[TOOL] HTTP request: POST http://localhost:6821/call_tool")
logger.debug("[TOOL] Request body: {json.dumps(args)}")
```

### Wire protocol (TRACE)
```python
logger.trace("[TOOL] Raw response: b'{\"status\":\"success\"...}'")
```

### Section boundaries
```python
logger.info("═" * 63)  # Major section (tool, model)
logger.info("─" * 63)  # Minor section (MCP)
```

## Benefits for LLM Agents

1. **Fast Navigation**: Grep for `[TOOL]` or `►►►` to find actions instantly
2. **Clear Timeline**: Start/end markers show execution flow
3. **Rich Metrics**: Timing, sizes, rates visible at INFO level
4. **Reduced Noise**: 84% fewer lines, 100% signal
5. **Lower Token Cost**: ~20k tokens vs ~122k tokens per session

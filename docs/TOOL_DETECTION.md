# Tool and Vision Capability Detection

## Overview

ChatLlama now automatically detects and displays model capabilities:
- **[Vision]** - Models that support image/vision input
- **[Tools]** - Models with built-in tool/function calling support

These badges appear in the model selection dropdown for quick identification.

## How Tool Detection Works

### Detection Method
Tool capability is detected by examining the **chat template** in GGUF metadata:

```
tokenizer.chat_template field → Check for tool-handling patterns
```

### Tool Markers Recognized

| Pattern | Example | Model(s) |
|---------|---------|----------|
| `{%- if tools` | `{%- if tools -%}` | Huihui-LFM2, Qwen3-VL series |
| `if tools` | `{% if tools` | Qwen3 models |
| `render_extra_keys` | Function wrapper | Nemotron |

### Models with Tools
- ✅ **Huihui-LFM2** - Small model with tool support
- ✅ **Huihui-Ministral** - Ministral variant with tools
- ✅ **Qwen3-VL-4B** - Vision model with tools
- ✅ **Qwen3-VL-8B** - Vision model with tools  
- ✅ **Qwen3-24B** - Text model with tools
- ✅ **Nemotron** - Large model with function calling
- ✅ **Devstral** - Mistral-based with tools

### Models WITHOUT Tools
- ❌ **olmOCR** - Vision-only OCR model (no tool support)
- ❌ **gemma-3-27b** - Text model without tools

## How Vision Detection Works

### Detection Method
Vision capability is detected by examining **GGUF metadata fields**:

```
GGUF fields → Look for vision-related keywords
mmproj file → Check for CLIP vision projection metadata
Filename → Check for "-VL-" or "vision" patterns
```

### Vision Keywords Recognized
- `vision`, `visual`, `image` - Generic vision indicators
- `clip` - CLIP vision encoder (common in multimodal models)
- `projector`, `mmproj` - Vision projection components

### Models with Vision
- ✅ **Qwen3-VL-4B** - Vision Language 4B
- ✅ **Qwen3-VL-8B** - Vision Language 8B
- ✅ **Huihui-Ministral** - Has vision projection (mmproj)
- ✅ **gemma-3-27b** - Has vision support
- ✅ **olmOCR** - Optical Character Recognition (CLIP-based)

### Models WITHOUT Vision
- ❌ **Huihui-LFM2** - Text-only model
- ❌ **Nemotron** - Text-only large model
- ❌ **Qwen3-24B** - Text thinking model
- ❌ **Devstral** - Text-only Mistral variant

## Implementation Details

### File Handling
The detector handles model directories containing multiple GGUF files:
- **Main model**: `Model-Name.Q4_K_S.gguf` (or similar quantization)
- **Vision projection**: `mmproj-Model-Name.gguf`

Strategy:
1. Prefer main model files for tool detection (has chat templates)
2. Also scan mmproj files for vision metadata
3. Combine results for complete capability picture

### GGUF Library Dependency
The feature requires the `gguf` Python library:
```bash
pip install gguf
```

If not installed, capability detection gracefully falls back to no capabilities (badges won't show).

## Code Location

- **Detection Logic**: [chat.py](chat.py#L87-L167) - `ModelCapabilities` class
- **UI Integration**: [chat.py](chat.py#L350-L360) - `_populate_models_with_capabilities()` method

## Example Output

In the model selection dropdown:

```
DavidAU\Qwen3-24B-A4B-Freedom-HQ-Thinking-Abliterated-Heretic-NEOMAX-Imatrix-GGUF [Tools]
lmstudio-community\Devstral-Small-2-24B-Instruct-2512-GGUF [Tools]
lmstudio-community\NVIDIA-Nemotron-3-Nano-30B-A3B-GGUF [Tools]
lmstudio-community\olmOCR-2-7B-1025-GGUF [Vision]
mradermacher\gemma-3-27b-it-abliterated-GGUF [Vision]
mradermacher\Huihui-LFM2-2.6B-Exp-abliterated-GGUF [Tools]
mradermacher\Huihui-Ministral-3-8B-Reasoning-2512-abliterated-GGUF [Tools] [Vision]
mradermacher\Qwen3-VL-4B-Instruct-abliterated-v2-GGUF [Tools] [Vision]
mradermacher\Qwen3-VL-8B-Instruct-abliterated-v2.0-GGUF [Tools] [Vision]
```

## Testing

Run the verification script to confirm detection accuracy:
```bash
python TOOL_DETECTION_SUMMARY.py
```

Expected output: All key models should show "VERIFIED" status.

## Future Enhancements

1. **Display tool lists** - Show what specific tools each model supports
2. **Performance note** - Indicate which models work well with tool calling
3. **Tool execution** - Actually invoke tools when model requests them
4. **Agent mode** - Toggle for multi-step tool reasoning

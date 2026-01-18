# ChatLlama Launch Parameters

## Overview
ChatLlama supports several command-line parameters to customize startup behavior and enable automation testing.

## Parameters

### `--model` - Specify Model at Startup
Loads a specific model without requiring manual selection in the UI.

**Supports two formats:**

#### 1. Relative Path (Discovery Format)
Uses the standard model discovery format from `D:\LLM Models\{author}\{model-name}`:

```powershell
python src/chat.py --model "mradermacher/Huihui-LFM2-2.6B-Exp-abliterated-GGUF"
```

#### 2. Full File Path (Direct GGUF Path)
Loads a specific GGUF file directly:

```powershell
python src/chat.py --model "D:\LLM Models\mradermacher\gemma-3-27b-it-abliterated-refined-vision-i1-GGUF\gemma-3-27b-it-abliterated-refined-vision.i1-Q3_K_S.gguf"
```

**Usage with Gemma 3 (Modern LLM with Tool Support):**

```powershell
# Load Gemma model directly
conda activate chatllama
python src/chat.py --model "D:\LLM Models\mradermacher\gemma-3-27b-it-abliterated-refined-vision-i1-GGUF\gemma-3-27b-it-abliterated-refined-vision.i1-Q3_K_S.gguf"
```

### `--input-file` - Automation Mode
Loads messages from a text file for automated testing. Each line is treated as a message to send to the model.

```powershell
python src/chat.py --input-file tests/test_input.txt
```

**File Format:**
- One message per line
- Lines starting with `#` are comments (ignored)
- Empty lines are ignored
- Use `EXIT`, `#EXIT`, `QUIT`, or `#QUIT` on a line to trigger app shutdown after model responds

Example `test_input.txt`:
```
# Test messages for automation
Hello, what is Python?
Explain machine learning briefly
EXIT
```

### `--list-models` - List Available Models
Lists all discovered models and exits without launching the UI.

```powershell
python src/chat.py --list-models
```

## Combined Usage

Load Gemma model and run automation tests:

```powershell
python src/chat.py --model "D:\LLM Models\mradermacher\gemma-3-27b-it-abliterated-refined-vision-i1-GGUF\gemma-3-27b-it-abliterated-refined-vision.i1-Q3_K_S.gguf" --input-file tests/test_gemma_tools.txt
```

## Notes

- **Full Paths**: Must point to existing GGUF files. The file is validated before loading.
- **Fallback**: If llama-cpp-python fails, the app automatically tries llama-server.
- **Context Size**: Uses value from settings.yml or spin box default (DEFAULT_CTX).
- **GPU Layers**: Always sets `n_gpu_layers=-1` to maximize GPU acceleration.
- **Logging**: All operations are logged to `chatllama.log` for debugging.

## Environment Setup

```powershell
conda activate chatllama
cd d:\_GITN\chatllama
```

Then run with your chosen parameters.

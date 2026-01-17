# ChatLlama Command-Line Arguments

## New Features Added

### 1. List Available Models
**Flag:** `--list-models`

Display all available models and exit immediately.

**Usage:**
```powershell
python chat.py --list-models
```

**Output Example:**
```
AVAILABLE MODELS
======================================================================
 1. DavidAU\Qwen3-24B-A4B-Freedom-HQ-Thinking-Abliterated-Heretic-NEOMAX-Imatrix-GGUF
 2. lmstudio-community\Devstral-Small-2-24B-Instruct-2512-GGUF
 3. lmstudio-community\NVIDIA-Nemotron-3-Nano-30B-A3B-GGUF
 4. lmstudio-community\olmOCR-2-7B-1025-GGUF
 5. mradermacher\Huihui-LFM2-2.6B-Exp-abliterated-GGUF
 6. mradermacher\Huihui-Ministral-3-8B-Reasoning-2512-abliterated-GGUF
 7. mradermacher\Qwen2.5-VL-7B-Abliterated-Caption-it-GGUF
 8. mradermacher\Qwen3-VL-4B-Instruct-abliterated-v2-GGUF
 9. mradermacher\Qwen3-VL-8B-Instruct-abliterated-v2.0-GGUF
10. mradermacher\gemma-3-27b-it-abliterated-GGUF
11. mradermacher\gemma-3-27b-it-abliterated-refined-vision-i1-GGUF
======================================================================
Total: 11 models found in D:\LLM Models
```

---

### 2. Set Model on Startup
**Flag:** `--model MODEL_NAME`

Load a specific model when the application starts. Bypasses the default model setting.

**Usage:**
```powershell
# Using backslash (Windows native path)
python chat.py --model "mradermacher\Huihui-Ministral-3-8B-Reasoning-2512-abliterated-GGUF"

# Using forward slash (also works)
python chat.py --model "mradermacher/Huihui-Ministral-3-8B-Reasoning-2512-abliterated-GGUF"
```

**Examples:**
```powershell
# Load a specific model directly
python chat.py --model "mradermacher\gemma-3-27b-it-abliterated-GGUF"

# Combine with automation mode
python chat.py --model "mradermacher\Huihui-LFM2-2.6B-Exp-abliterated-GGUF" --input-file test_input.txt

# Chain with help
python chat.py --help
```

---

## Complete Usage Reference

### Help
```powershell
python chat.py --help
```

### List Models
```powershell
python chat.py --list-models
```

### Load Default Model
```powershell
python chat.py
```

### Load Specific Model
```powershell
python chat.py --model "mradermacher\Huihui-LFM2-2.6B-Exp-abliterated-GGUF"
```

### Automation with Default Model
```powershell
python chat.py --input-file test_input.txt
```

### Automation with Specific Model
```powershell
python chat.py --model "mradermacher\Huihui-Ministral-3-8B-Reasoning-2512-abliterated-GGUF" --input-file test_input.txt
```

---

## Implementation Details

### Code Changes

**1. Added Static Method for Model Discovery**
- `_discover_models_static()` - Can be called without ChatWindow instance
- Enables `--list-models` to work before GUI initialization

**2. Updated Constructor**
- Added `selected_model` parameter to `__init__()`
- Stores command-line model selection

**3. Enhanced Model Loading**
- `_load_default_model()` checks for `--model` argument
- Falls back to `settings.yml` default if not specified
- Properly sets combo box selection

**4. Argument Parser**
- `--list-models` - Action 'store_true' (boolean flag)
- `--model` - Type 'str' (accepts model name/path)
- Both work with existing `--input-file`/`--test-file`

---

## Use Cases

### Finding Available Models
```powershell
# See all installed models
python chat.py --list-models | findstr "Qwen"
```

### Quick Model Switching
```powershell
# Test different models with same input
python chat.py --model "mradermacher\gemma-3-27b-it-abliterated-GGUF" --input-file test.txt
python chat.py --model "lmstudio-community\NVIDIA-Nemotron-3-Nano-30B-A3B-GGUF" --input-file test.txt
```

### CI/CD Integration
```powershell
# List models in pipeline
python chat.py --list-models > available_models.txt

# Run automated tests with specific model
foreach($model in $models) {
    python chat.py --model $model --input-file regression_tests.txt
}
```

### Scripting
```powershell
# Get model count
$count = (python chat.py --list-models | Select-String "^[0-9]").Count
Write-Host "Found $count models"

# Find vision models
python chat.py --list-models | Select-String -Pattern "VL|Vision|vision"
```

---

## Notes

- Model names are case-sensitive
- Use either `\` or `/` as path separators (both work)
- Exit code is 0 for successful operations
- All model discovery is logged to `chatllama.log`
- Session logs created in `logs/` directory

# Vision-Based Log Analysis for ChatLlama

## Overview

ChatLlama now captures **both full screenshots and individual card SVG images** when sessions complete. These images can be analyzed using vision-capable LLMs to understand what was displayed.

## Automatic Capture

### What Gets Captured

1. **Full Window Screenshot**: `logs/session_YYYY-MM-DD_HH-MM-SS.png`
   - Shows entire ChatLlama UI (Settings, Chat, Cards, Trace columns)
   - Captured when:
     - Automation mode completes (EXIT marker detected)
     - App window closes normally

2. **Card SVG Images**: `logs/session_YYYY-MM-DD_HH-MM-SS_cardsvg01.png`
   - Individual card widget images showing SVG/graphics output
   - Numbered sequentially (`_cardsvg01.png`, `_cardsvg02.png`, etc.)
   - Captures the actual rendered content in the Cards panel

### Example Files

```
logs/
├── session_2026-01-19_01-38-53.log          # Text log
├── session_2026-01-19_01-38-53.png          # Full screenshot
└── session_2026-01-19_01-38-53_cardsvg01.png # Card SVG export
```

## Analysis Workflow

### Step 1: Run a Test Session

```powershell
# Run automation test
python src\chat.py --input-file tests\test_svg_magazine_cover.txt

# Images are automatically captured on completion
```

### Step 2: Generate Vision Analysis Prompt

```powershell
# List available sessions with card images
python src\analyze_logs_with_vision.py

# Generate prompt for a specific session
python src\analyze_logs_with_vision.py --log-session session_2026-01-19_01-38-53 --prompt-only
```

This outputs a formatted prompt like:

```
I captured 1 images from a ChatLlama session. Please analyze them:

Image 1: session_2026-01-19_01-38-53_cardsvg01.png

For each image, describe:
1. The overall layout and composition
2. Any text content and what it says
3. The type of content (SVG, graphics, demo, etc.)
4. The quality and clarity of rendering
5. Any notable features or issues

Format your response as JSON with keys for each image.
```

### Step 3: Analyze with Vision LLM

**Option A: Use ChatLlama UI** (Recommended)

1. Start ChatLlama
2. Load a vision-capable model (e.g., Qwen3-VL, gemma-3-27b-it-abliterated-refined-vision)
3. Paste the generated prompt
4. **Drag and drop** the card image(s) onto the input area
5. Send the message

The LLM will analyze the images and describe what it sees.

**Option B: Command Line Vision Model**

```powershell
# Use a vision model directly (requires vision-capable model)
# Example with Qwen3-VL or similar
python -c "
from llama_cpp import Llama
model = Llama(model_path='...', n_ctx=4096)
# Load image and prompt...
"
```

### Step 4: Generate Analysis Report

```powershell
# Create JSON report of captured images
python src\analyze_logs_with_vision.py --log-session session_2026-01-19_01-38-53 --report analysis_report.json
```

Output:
```json
{
  "session": "session_2026-01-19_01-38-53",
  "timestamp": "2026-01-19T01:40:00",
  "images": {
    "count": 1,
    "files": [
      "D:\\_GITN\\chatllama\\logs\\session_2026-01-19_01-38-53_cardsvg01.png"
    ]
  },
  "images_exist": true,
  "next_step": "Open these images in ChatLlama UI and ask the LLM to describe them"
}
```

## Use Cases

### 1. **Verify SVG Rendering Quality**

Analyze card exports to ensure:
- SVG elements render correctly
- Text is readable
- Layout follows rules
- No visual artifacts or errors

### 2. **Debug Tool Output**

When MCPs generate visual content:
- Verify the output matches the tool's intent
- Check for rendering issues
- Validate against expected layout

### 3. **Automated Testing**

In CI/CD pipelines:
1. Run automation tests
2. Capture card images
3. Use vision LLM to validate output
4. Compare against golden images or expected descriptions

### 4. **Documentation**

Generate documentation showing:
- What the LLM produced
- How SVG tools render content
- Visual examples of MCP tool output

## Vision Model Requirements

**Supported Models** (with vision capability):
- Qwen3-VL series (4B, 8B)
- Gemma-3-27B with vision refinement
- Any GGUF model with "👁️" vision icon in ChatLlama

**Model Requirements**:
- Vision input support (image embeddings)
- Sufficient context window (4K+ recommended)
- GGUF format compatible with llama-cpp-python

## Tips for Best Results

1. **Use High-Quality Captures**: Card exports are lossless PNG format
2. **Be Specific in Prompts**: Ask for specific aspects (layout, text, quality, etc.)
3. **Request Structured Output**: JSON format helps parse LLM analysis programmatically
4. **Compare Multiple Sessions**: Track rendering improvements across runs
5. **Automate Validation**: Script vision analysis to validate automated tests

## Example: SVG Magazine Cover Analysis

```powershell
# Run the magazine cover test
python src\chat.py --input-file tests\test_svg_magazine_cover.txt

# Generate analysis prompt
python src\analyze_logs_with_vision.py --log-session session_2026-01-19_01-38-53 --prompt-only > prompt.txt

# In ChatLlama UI with vision model:
# 1. Paste prompt from prompt.txt
# 2. Drag logs/session_2026-01-19_01-38-53_cardsvg01.png into input
# 3. Send

# LLM will describe:
# - Layout structure (SVG demo with text and image)
# - Content (header, bullet points, feature image)
# - Quality (rendering sharpness, color accuracy)
# - Any issues or improvements
```

## Implementation Details

### Code Changes

1. **`src/chat.py`**:
   - `_capture_card_svgs()`: Export card widgets as PNG images
   - Called alongside `_capture_screenshot()` on app close and automation exit

2. **`src/analyze_logs_with_vision.py`**:
   - Utility to find, organize, and generate prompts for vision analysis
   - No direct vision model integration (uses ChatLlama UI for analysis)

### File Naming Convention

```
session_<timestamp>.log           # Text log
session_<timestamp>.png           # Full screenshot
session_<timestamp>_cardsvg01.png # Card 1 export
session_<timestamp>_cardsvg02.png # Card 2 export (if multiple cards)
```

## Future Enhancements

- [ ] Multi-card support (when CardsPanel supports multiple cards)
- [ ] Direct vision model integration in utility script
- [ ] Automated comparison with golden images
- [ ] Vision-based test assertions
- [ ] Render diff visualization

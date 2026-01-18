## Quick Start with Gemma Model

The ChatLlama app now supports direct model loading via command-line parameters. Here's how to test with the Gemma 3 model:

### Load Gemma with Full Path

```powershell
conda activate chatllama
cd d:\_GITN\chatllama
python src/chat.py --model "D:\LLM Models\mradermacher\gemma-3-27b-it-abliterated-refined-vision-i1-GGUF\gemma-3-27b-it-abliterated-refined-vision.i1-Q3_K_S.gguf"
```

This will:
1. Launch the ChatLlama UI
2. Automatically load the Gemma model on startup
3. Skip the manual model selection step
4. Show model name in status bar and settings panel

### Test with Automation Mode

Load Gemma and run automated tests:

```powershell
python src/chat.py --model "D:\LLM Models\mradermacher\gemma-3-27b-it-abliterated-refined-vision-i1-GGUF\gemma-3-27b-it-abliterated-refined-vision.i1-Q3_K_S.gguf" --input-file tests/test_gemma_tools.txt
```

This will:
1. Load Gemma model
2. Execute messages from `tests/test_gemma_tools.txt`
3. Automatically exit after the `EXIT` marker
4. Log all interactions to `logs/session_*.log`

### What to Expect

The test file includes:
- **Regular question**: "What is the capital of France?" (no tools needed)
- **Fashion question**: "Can you suggest a nice fashion look..." (may use fashion tools)
- **Tool query**: "What are some popular fashion looks available?" (list all tools)

### Gemma Tool Support

Gemma 3 is a modern LLM with proper tool calling support. It understands the `tools` parameter passed to `create_chat_completion()` and can invoke tools when needed.

See `docs/LAUNCH_PARAMETERS.md` for complete parameter documentation.

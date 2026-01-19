#!/usr/bin/env python3
"""Test loading Gemma-3 27B directly with llama-cpp-python (should work)."""

import os
import sys
from pathlib import Path

# Fix encoding for Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Configure environment for C:\Llama DLLs
os.environ["LLAMA_CPP_LIB"] = r"C:\Llama\llama.dll"
os.add_dll_directory(r"C:\Llama")

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from llama_cpp import Llama

MODEL_PATH = r"D:\LLM Models\mradermacher\gemma-3-27b-it-abliterated-GGUF"

# Find the actual GGUF file
model_dir = Path(MODEL_PATH)
gguf_files = sorted(model_dir.glob("*.gguf"))
if not gguf_files:
    print(f"❌ No GGUF files found in {MODEL_PATH}")
    sys.exit(1)

quantized = [f for f in gguf_files if "Q" in f.name.upper() and "mmproj" not in f.name.lower()]
if not quantized:
    quantized = [f for f in gguf_files if "mmproj" not in f.name.lower()]

model_file = quantized[0] if quantized else gguf_files[0]

print("=" * 80)
print("Testing Gemma-3 27B with native llama-cpp-python")
print(f"Model: {model_file}")
print(f"LLAMA_CPP_LIB: {os.environ.get('LLAMA_CPP_LIB')}")
print("=" * 80)

try:
    print("\n[1] Creating Llama instance...")
    llm = Llama(
        model_path=str(model_file),
        n_gpu_layers=99,
        n_ctx=2048,
        verbose=False,
    )
    print("[OK] Model loaded successfully!")
    
    print("\n[2] Testing chat completion...")
    response = llm.create_chat_completion(
        messages=[{"role": "user", "content": "Hi"}],
        stream=False,
    )
    print("[OK] Chat completion successful!")
    print(f"Response: {response['choices'][0]['message']['content']}")
    
except Exception as e:
    print(f"[ERROR] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

#!/usr/bin/env python3
"""Test loading Devstral directly with llama-cpp-python (no llama-server)."""

import os
import sys
from pathlib import Path

# Configure environment for C:\Llama DLLs
os.environ["LLAMA_CPP_LIB"] = r"C:\Llama\llama.dll"
os.add_dll_directory(r"C:\Llama")

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from llama_cpp import Llama

MODEL_PATH = r"D:\LLM Models\lmstudio-community\Devstral-Small-2-24B-Instruct-2512-GGUF\Devstral-Small-2-24B-Instruct-2512-Q3_K_L.gguf"

print("=" * 80)
print("Testing Devstral with native llama-cpp-python")
print(f"Model: {MODEL_PATH}")
print(f"LLAMA_CPP_LIB: {os.environ.get('LLAMA_CPP_LIB')}")
print("=" * 80)

try:
    print("\n[1] Creating Llama instance...")
    llm = Llama(
        model_path=MODEL_PATH,
        n_gpu_layers=99,
        n_ctx=2048,
        verbose=False,
    )
    print("✅ Model loaded successfully!")
    
    print("\n[2] Testing chat completion...")
    response = llm.create_chat_completion(
        messages=[{"role": "user", "content": "Hi"}],
        stream=False,
    )
    print("✅ Chat completion successful!")
    print(f"Response: {response['choices'][0]['message']['content']}")
    
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

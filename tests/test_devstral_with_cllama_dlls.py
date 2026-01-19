#!/usr/bin/env python3
"""Verify that llama-cpp-python is using C:\Llama DLLs."""

import os
import sys

# Must be set BEFORE importing llama_cpp
os.environ["LLAMA_CPP_LIB"] = r"C:\Llama\llama.dll"
os.add_dll_directory(r"C:\Llama")

print(f"LLAMA_CPP_LIB = {os.environ.get('LLAMA_CPP_LIB')}")
print(f"DLL directories configured: C:\\Llama")

from llama_cpp import Llama
import llama_cpp

print(f"\nllama_cpp module location: {llama_cpp.__file__}")
print(f"llama_cpp version: {llama_cpp.__version__}")

# Check if it's using the C:\Llama libraries
try:
    # Try to access the underlying library
    if hasattr(llama_cpp, '_lib'):
        print(f"Loaded library: {llama_cpp._lib}")
except Exception as e:
    print(f"Could not inspect library: {e}")

# Now test loading a model
print("\n" + "="*80)
print("Testing Devstral with llama-cpp-python pointing to C:\\Llama\\llama.dll")
print("="*80)

MODEL_PATH = r"D:\LLM Models\lmstudio-community\Devstral-Small-2-24B-Instruct-2512-GGUF\Devstral-Small-2-24B-Instruct-2512-Q3_K_L.gguf"

try:
    print("\n[1] Creating Llama instance...")
    llm = Llama(
        model_path=MODEL_PATH,
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
    content = response['choices'][0]['message']['content']
    print(f"Response: {content[:100]}...")
    
except Exception as e:
    print(f"[ERROR] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

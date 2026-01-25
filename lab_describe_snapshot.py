"""
Quick UI Screenshot Analyzer using Moondream2 (1.8B)
Fast, local, small model perfect for UI analysis.
Standalone test script for debugging Moondream integration.
"""
import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import sys
from pathlib import Path
from PIL import Image
import time
import threading

print("=" * 70)
print("Moondream2 Screenshot Analyzer - Standalone Test")
print("=" * 70)

# Check for transformers
print("\n[1/5] Checking transformers library...")
try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    print("OK: transformers library available")
except ImportError as e:
    print(f"ERROR: transformers not available: {e}")
    sys.exit(1)

# Get screenshot path
if len(sys.argv) < 2:
    # Use most recent screenshot from logs folder
    logs_folder = Path(r"D:\_GITN\chatllama\pepper_settings\logs")
    screenshots = sorted(logs_folder.glob("session_*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    if screenshots:
        screenshot_path = str(screenshots[0])
        print(f"\n[2/5] No argument provided, using most recent screenshot:")
        print(f"      {screenshot_path}")
    else:
        print("\n✗ No screenshot found in logs folder and no argument provided")
        print("Usage: python lab_describe_snapshot.py <path_to_screenshot.png>")
        sys.exit(1)
else:
    screenshot_path = sys.argv[1]
    print(f"\n[2/5] Using provided screenshot:")
    print(f"      {screenshot_path}")

# Verify file exists
if not Path(screenshot_path).exists():
    print(f"✗ File not found: {screenshot_path}")
    sys.exit(1)
print(f"OK: File exists ({Path(screenshot_path).stat().st_size:,} bytes)")

# Load image
print("\n[3/5] Loading image with PIL...")
try:
    image = Image.open(screenshot_path)
    print(f"OK: Image loaded: {image.size[0]}x{image.size[1]} pixels, mode={image.mode}")
except Exception as e:
    print(f"ERROR: Failed to load image: {e}")
    sys.exit(1)

# Load Moondream model
MODEL_ID = "vikhyatk/moondream2"
print(f"\n[4/5] Loading {MODEL_ID}...")
print("      (first run will download ~3.5GB from HuggingFace)")
print("      This may take 2-5 minutes depending on your connection...")

model = None
tokenizer = None
load_error = None
load_done = threading.Event()

def _load_model_background() -> None:
    global model, tokenizer, load_error
    start_time = time.time()
    try:
        print("      [bg] Loading model...")
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            trust_remote_code=True,
            device_map="auto"  # Auto-select GPU if available
        )
        print("      [bg] Loading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        elapsed = time.time() - start_time
        print(f"OK: [bg] Model loaded successfully in {elapsed:.1f}s")
    except Exception as e:
        elapsed = time.time() - start_time
        load_error = e
        print(f"ERROR: [bg] Failed to load model after {elapsed:.1f}s:")
        print(f"   {type(e).__name__}: {e}")
    finally:
        load_done.set()

threading.Thread(target=_load_model_background, daemon=True).start()

while not load_done.wait(timeout=1.0):
    print("      [bg] Loading still in progress...")

if load_error is not None or model is None or tokenizer is None:
    sys.exit(1)

# Generate description
print("\n[5/5] Generating description...")
question = "Describe this user interface layout in detail. What are the main sections, content areas, and any layout features you notice?"

try:
    start_time = time.time()
    answer = model.answer_question(image, question, tokenizer)
    elapsed = time.time() - start_time
    print(f"OK: Description generated in {elapsed:.1f}s")
except Exception as e:
    print(f"ERROR: Failed to generate description: {e}")
    sys.exit(1)

# Display results
print("\n" + "=" * 70)
print("RESULT")
print("=" * 70)
print(f"\nQuestion: {question}")
print(f"\nAnswer:\n{answer}")
print("\n" + "=" * 70)

# Save to file
output_path = Path(screenshot_path).with_suffix(".txt")
try:
    output_path.write_text(f"Question: {question}\n\nAnswer:\n{answer}\n", encoding="utf-8")
    print(f"\nOK: Description saved to: {output_path}")
except Exception as e:
    print(f"\nWARN: Could not save description file: {e}")

print("\n" + "=" * 70)
print("Test completed successfully!")
print("=" * 70)

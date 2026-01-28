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

# Get screencap + card paths
args = sys.argv[1:]
output_override: Path | None = None
if "--output" in args:
    idx = args.index("--output")
    if idx + 1 < len(args):
        output_override = Path(args[idx + 1])
        del args[idx : idx + 2]

provided_paths = [Path(p) for p in args]
if not provided_paths:
    logs_folder = Path(r"D:\_GITN\chatllama\pepper_settings\logs")
    screencaps = sorted(logs_folder.glob("*/screencap.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    if screencaps:
        provided_paths = [screencaps[0]]
        print("\n[2/5] No argument provided, using most recent screencap:")
        print(f"      {provided_paths[0]}")
    else:
        screenshots = sorted(logs_folder.glob("session_*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
        if screenshots:
            provided_paths = [screenshots[0]]
            print("\n[2/5] No argument provided, using most recent screenshot:")
            print(f"      {provided_paths[0]}")
        else:
            print("\n✗ No screenshot found in logs folder and no argument provided")
            print("Usage: python lab_describe_snapshot.py <path_to_screencap.png> [card1.png ... cardN.png]")
            sys.exit(1)
else:
    print("\n[2/5] Using provided images:")
    for item in provided_paths:
        print(f"      {item}")

screencap_path = provided_paths[0]
card_paths = provided_paths[1:]

# Verify files exist
missing = [path for path in provided_paths if not path.exists()]
if missing:
    print("✗ File(s) not found:")
    for path in missing:
        print(f"   {path}")
    sys.exit(1)
print(f"OK: Files found ({len(provided_paths)} total)")

# Load Moondream model
MODEL_ID = "vikhyatk/moondream2"
MODEL_SLUG = "models--vikhyatk--moondream2"

def _find_hf_cache_root() -> Path | None:
    env_cache = os.environ.get("HF_HUB_CACHE")
    if env_cache:
        return Path(env_cache)
    env_home = os.environ.get("HF_HOME")
    if env_home:
        return Path(env_home) / "hub"
    return Path.home() / ".cache" / "huggingface" / "hub"


def _has_cached_model(cache_root: Path) -> bool:
    return (cache_root / MODEL_SLUG).exists()
cache_root = _find_hf_cache_root()
cache_ready = cache_root is not None and _has_cached_model(cache_root)

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
        if cache_ready:
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        print("      [bg] Loading model...")
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            trust_remote_code=True,
            device_map="auto",  # Auto-select GPU if available
            local_files_only=cache_ready,
        )
        print("      [bg] Loading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(
            MODEL_ID,
            local_files_only=cache_ready,
        )
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

def _describe_image(image_path: Path, prompt: str) -> str:
    image = Image.open(image_path)
    start_time = time.time()
    answer = model.answer_question(image, prompt, tokenizer)
    elapsed = time.time() - start_time
    print(f"OK: Description generated for {image_path.name} in {elapsed:.1f}s")
    return answer


def _description_path_from_screencap(path: Path) -> Path:
    if output_override is not None:
        return output_override
    return path.with_name("description.txt")


print("\n[5/5] Generating descriptions...")
screen_question = "Describe this user interface layout in detail. What are the main sections, content areas, and any layout features you notice?"
card_question = "Describe this card in detail. Mention imagery, layout, text, and colors."

sections: list[str] = []

try:
    answer = _describe_image(screencap_path, screen_question)
    sections.append("Screen Capture")
    sections.append(f"Question: {screen_question}\n\nAnswer:\n{answer}")

    for index, card_path in enumerate(card_paths, start=1):
        card_answer = _describe_image(card_path, card_question)
        sections.append(f"Card {index}")
        sections.append(f"Question: {card_question}\n\nAnswer:\n{card_answer}")
except Exception as e:
    print(f"ERROR: Failed to generate description: {e}")
    sys.exit(1)

output_path = _description_path_from_screencap(screencap_path)
try:
    output_path.write_text("\n\n".join(sections) + "\n", encoding="utf-8")
    print(f"\nOK: Description saved to: {output_path}")
except Exception as e:
    print(f"\nWARN: Could not save description file: {e}")

print("\n" + "=" * 70)
print("Test completed successfully!")
print("=" * 70)

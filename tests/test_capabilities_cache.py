#!/usr/bin/env python3
"""
Test capabilities caching system
"""
import yaml
from pathlib import Path

settings_file = Path("settings.yml")

# Read current settings
with open(settings_file, 'r') as f:
    settings = yaml.safe_load(f)

print("\n" + "="*100)
print("CAPABILITIES CACHE TEST")
print("="*100)

cache = settings.get("model_capabilities", {})

if not cache:
    print("\nNo cached capabilities found. First run will scan all models.")
    print("Expected behavior: Progress dialog will appear during initial scan.")
else:
    print(f"\nFound cached capabilities for {len(cache)} models:")
    
    for model_name, caps in list(cache.items())[:5]:  # Show first 5
        print(f"\n{model_name}:")
        print(f"  Vision: {caps.get('has_vision', False)}")
        print(f"  Tools: {caps.get('has_tools', False)}")
        print(f"  Context: {caps.get('context_length', 0):,} tokens")
        print(f"  VRAM: {caps.get('vram_mb', 0)} MB")
    
    if len(cache) > 5:
        print(f"\n... and {len(cache) - 5} more models")

print("\n" + "="*100)
print("EXPECTED BEHAVIOR ON STARTUP")
print("="*100)

print("""
First Run:
  - No cache exists in settings.yml
  - Progress dialog shows: "Scanning model capabilities..."
  - Each model scanned for vision, tools, context_length
  - Cache saved to settings.yml
  - Next runs use cached data instantly

Subsequent Runs:
  - Cache loaded from settings.yml
  - Model list populated immediately (no scanning)
  - New models detected and added to cache

Cache Format in settings.yml:
  model_capabilities:
    author\model-name:
      has_vision: true/false
      has_tools: true/false
      context_length: 8192
      vram_mb: 0  # Populated when model is loaded

Manual Refresh:
  - Delete "model_capabilities:" section from settings.yml
  - Restart app to trigger full rescan
""")

print("="*100)

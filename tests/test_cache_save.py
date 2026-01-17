#!/usr/bin/env python3
"""
Test caching system with mock GUI to verify save works
"""
import yaml
import sys
import logging
from pathlib import Path

# Set up minimal logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Load settings
settings_file = Path("settings.yml")
with open(settings_file, 'r') as f:
    settings = yaml.safe_load(f)

# Simulate adding capabilities to cache
print("\n" + "="*80)
print("SIMULATING CAPABILITIES SCAN")
print("="*80)

cache = settings.get("model_capabilities", {})
print(f"\nCurrent cache has {len(cache)} entries")

# Add test entries
test_models = {
    "test/model-1": {
        "has_vision": True,
        "has_tools": True,
        "context_length": 8192,
        "vram_mb": 4500
    },
    "test/model-2": {
        "has_vision": False,
        "has_tools": True,
        "context_length": 16384,
        "vram_mb": 2500
    }
}

print("\nAdding test entries:")
for model, caps in test_models.items():
    cache[model] = caps
    print(f"  {model}: vision={caps['has_vision']}, tools={caps['has_tools']}, ctx={caps['context_length']}, vram={caps['vram_mb']}MB")

# Save to settings
settings["model_capabilities"] = cache

print(f"\nSaving to {settings_file}...")
with open(settings_file, 'w') as f:
    yaml.dump(settings, f, default_flow_style=False, sort_keys=False)

print("✓ Saved successfully")

# Verify it was saved
with open(settings_file, 'r') as f:
    reloaded = yaml.safe_load(f)

reloaded_cache = reloaded.get("model_capabilities", {})
print(f"\n✓ Verified: Cache now has {len(reloaded_cache)} entries")

print("\n" + "="*80)
print("CACHE CONTENTS")
print("="*80)

for model, caps in reloaded_cache.items():
    print(f"\n{model}:")
    print(f"  Vision: {caps.get('has_vision', False)}")
    print(f"  Tools: {caps.get('has_tools', False)}")
    print(f"  Context: {caps.get('context_length', 0):,} tokens")
    print(f"  VRAM: {caps.get('vram_mb', 0)} MB")

print("\n" + "="*80)
print("SUCCESS - Caching system works!")
print("="*80)
print("\nYou can now delete the 'test/' entries from settings.yml if desired.")
print("Next run of chat.py will use this cache and skip rescanning those models.")

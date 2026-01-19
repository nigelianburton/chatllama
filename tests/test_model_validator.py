"""Test program for ModelValidator refactoring.

Tests:
1. Model discovery from filesystem
2. Capabilities cache loading
3. Model scanning and caching
"""

import sys
from pathlib import Path

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from chatllama_MODELS import ModelValidator
import yaml
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Mock ModelCapabilities class for testing
class MockModelCapabilities:
    @staticmethod
    def get_capabilities(model_path: Path, measure_vram: bool = False):
        """Mock capabilities - just return defaults."""
        return {
            "has_vision": False,
            "has_tools": False,
            "context_length": 8192,
            "vram_mb": 0,
            "display_name": model_path.stem
        }

def main():
    print("=" * 60)
    print("ModelValidator Test Program")
    print("=" * 60)
    
    # Load settings
    config_dir = PROJECT_ROOT / "config"
    settings_file = config_dir / "settings.yml"
    
    if not settings_file.exists():
        print(f"ERROR: Settings file not found: {settings_file}")
        return 1
    
    with open(settings_file, 'r') as f:
        settings = yaml.safe_load(f)
    
    models_dir = Path(settings.get("models_dir", r"D:\LLM Models"))
    
    print(f"\nModels Directory: {models_dir}")
    print(f"Settings File: {settings_file}")
    print(f"Models Dir Exists: {models_dir.exists()}")
    
    # Create validator
    validator = ModelValidator(
        models_dir=models_dir,
        settings_file=settings_file,
        settings=settings,
        model_capabilities_class=MockModelCapabilities,
        parent_widget=None
    )
    
    # Test 1: Model Discovery
    print("\n" + "=" * 60)
    print("TEST 1: Model Discovery")
    print("=" * 60)
    
    models = validator.discover_models()
    print(f"\nDiscovered {len(models)} models:")
    for i, model in enumerate(models, 1):
        print(f"  {i}. {model}")
    
    # Test 2: Capabilities Cache
    print("\n" + "=" * 60)
    print("TEST 2: Capabilities Cache")
    print("=" * 60)
    
    cache = validator.get_capabilities_cache()
    print(f"\nCached capabilities for {len(cache)} models:")
    for model_name, caps in list(cache.items())[:5]:  # Show first 5
        vision = "👁️" if caps.get("has_vision") else "  "
        tools = "🔧" if caps.get("has_tools") else "  "
        ctx = caps.get("context_length", 0) // 1000
        vram = caps.get("vram_mb", 0) / 1024
        print(f"  {vision} {tools} {model_name}")
        print(f"      Context: {ctx}k tokens, VRAM: {vram:.1f}GB")
    
    if len(cache) > 5:
        print(f"  ... and {len(cache) - 5} more")
    
    # Test 3: Check for missing models
    print("\n" + "=" * 60)
    print("TEST 3: Missing Models Check")
    print("=" * 60)
    
    cached_models = set(cache.keys())
    discovered_models = set(models)
    
    missing = cached_models - discovered_models
    new = discovered_models - cached_models
    
    if missing:
        print(f"\n⚠️  Models in cache but not on disk ({len(missing)}):")
        for model in list(missing)[:10]:
            print(f"  - {model}")
        if len(missing) > 10:
            print(f"  ... and {len(missing) - 10} more")
    else:
        print("\n✓ No missing models (cache is clean)")
    
    if new:
        print(f"\n📝 New models not yet cached ({len(new)}):")
        for model in list(new)[:10]:
            print(f"  + {model}")
        if len(new) > 10:
            print(f"  ... and {len(new) - 10} more")
    else:
        print("\n✓ All models are cached")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Models on disk:    {len(models)}")
    print(f"Models in cache:   {len(cache)}")
    print(f"Missing from disk: {len(missing)}")
    print(f"Not yet cached:    {len(new)}")
    print("\n✓ ModelValidator test complete")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

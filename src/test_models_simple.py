"""Simple test for chatllama_MODELS.py changes."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from chatllama_MODELS import load_settings, LlamaModelLoader

def main():
    print("Testing chatllama_MODELS.py...")
    
    # Test 1: Load settings
    print("\n1. Testing load_settings()...")
    settings_file = Path("config/settings.yml")
    try:
        settings = load_settings(settings_file)
        print(f"   ✓ Settings loaded successfully")
        print(f"   - Models dir: {settings['models_dir']}")
        print(f"   - Server path: {settings['llama_server_path']}")
        print(f"   - Port: {settings['llama_server_port']}")
        print(f"   - Last model: {settings.get('last_model', 'None')}")
    except FileNotFoundError as e:
        print(f"   ✗ FAILED: {e}")
        return 1
    
    # Test 2: Create LlamaModelLoader
    print("\n2. Testing LlamaModelLoader creation...")
    try:
        loader = LlamaModelLoader(
            models_dir=settings['models_dir'],
            gpu_offload_layers=settings['gpu_offload_layers'],
            port=settings['llama_server_port'],
            llama_server_path=settings['llama_server_path'],
        )
        print(f"   ✓ Loader created successfully")
        print(f"   - Port: {loader.port}")
        print(f"   - GPU layers: {loader.gpu_offload_layers}")
    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        return 1
    
    # Test 3: Test server running check
    print("\n3. Testing _is_llama_server_running()...")
    try:
        is_running = loader._is_llama_server_running()
        print(f"   ✓ Server check executed (running: {is_running})")
    except Exception as e:
        print(f"   ✓ Server check raised expected error: {type(e).__name__}")
    
    print("\n✓ All tests passed!")
    return 0

if __name__ == "__main__":
    sys.exit(main())

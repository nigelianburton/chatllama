"""Test llama-server integration with Devstral model"""
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from chatllama_MODELS import LlamaModelLoader, load_and_extract_settings


def test_llama_server_with_devstral():
    """Test that llama-server can load Devstral via LlamaModelLoader"""
    
    print("\n" + "="*80)
    print("TEST: llama-server Integration with Devstral Model")
    print("="*80 + "\n")
    
    # Load config
    settings_file = Path(__file__).parent.parent / "config" / "settings.yml"
    config = load_and_extract_settings(settings_file)
    
    print(f"[OK] Configuration loaded")
    print(f"  - Backend path: {config['llama_cpp_backend_path']}")
    print(f"  - Models dir: {config['models_dir']}")
    print(f"  - Server port: {config['llama_server_port']}\n")
    
    # Create loader
    loader = LlamaModelLoader(
        models_dir=config['models_dir'],
        llama_class=config['llama_class'],
        llama_cpp_backend_path=config['llama_cpp_backend_path'],
        gpu_offload_layers=config['gpu_offload_layers'],
        port=config['llama_server_port'],
        fallback_to_llama_server=True  # Enable fallback for this test
    )
    
    # Find Devstral model
    devstral_dir = Path(config['models_dir']) / "lmstudio-community" / "Devstral-Small-2-24B-Instruct-2512-GGUF"
    
    print(f"Looking for Devstral model in: {devstral_dir}")
    print(f"Directory exists: {devstral_dir.exists()}\n")
    
    if not devstral_dir.exists():
        print("[FAIL] Devstral directory not found!")
        return False
    
    # Resolve model file
    model_file, error_msg = loader.resolve_model_file(devstral_dir)
    if not model_file:
        print(f"[FAIL] Failed to resolve model file: {error_msg}")
        return False
    
    print(f"[OK] Model file resolved:")
    print(f"  - Path: {model_file}")
    print(f"  - Exists: {Path(model_file).exists()}\n")
    
    # Attempt to load model
    print("Loading model with LlamaModelLoader (will auto-fallback to llama-server)...")
    print("This may take 30-60 seconds for a 24B model...\n")
    
    try:
        result = loader.load_model_file(model_file, desired_ctx=2048)
        
        print(f"\n[OK] Load attempt completed!")
        print(f"  - Success: {result.success}")
        print(f"  - Used llama-server: {result.used_llama_server}")
        print(f"  - Message: {result.message}")
        
        if result.error:
            print(f"  - Error: {result.error}")
        
        if result.success:
            print(f"\n[SUCCESS] Model loaded successfully!")
            if result.used_llama_server:
                print("    Using llama-server backend (expected for Devstral with older llama-cpp-python)")
            print(f"    Model object: {type(result.model)}")
        else:
            print(f"\n[FAIL] FAILED to load model")
        
        return result.success
        
    except Exception as e:
        print(f"\n[FAIL] Exception during load: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_llama_server_with_devstral()
    sys.exit(0 if success else 1)

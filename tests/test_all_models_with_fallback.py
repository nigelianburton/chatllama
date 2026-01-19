"""Comprehensive test of all 7 models with llama-server fallback enabled"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from chatllama_MODELS import LlamaModelLoader, load_and_extract_settings


# All 7 models with their locations
MODELS = [
    ("Gemma 3", "mradermacher/gemma-3n-E4B-it-abliterated-i1-GGUF"),
    ("Qwen2.5-VL", "Qwen/Qwen2.5-VL-32B-Instruct-GGUF"),
    ("Gemma 3 27B", "mradermacher/gemma-3-27b-it-abliterated-i1-GGUF"),
    ("Devstral", "lmstudio-community/Devstral-Small-2-24B-Instruct-2512-GGUF"),
    ("Qwen3-VL v2", "lmstudio-community/Qwen3-VL-32B-Instruct-2405-GGUF"),
    ("Qwen3-VL v1", "lmstudio-community/Qwen3-VL-Instruct-1B-v2-GGUF"),
    ("Huihui-Ministral", "lmstudio-community/Huihui-Ministral-2.4B-Exp-GGUF"),
]


def test_all_models():
    """Test loading all 7 models with llama-server fallback enabled"""
    
    print("\n" + "="*80)
    print("COMPREHENSIVE TEST: All 7 Models with llama-server Fallback")
    print("="*80 + "\n")
    
    # Load config
    settings_file = Path(__file__).parent.parent / "config" / "settings.yml"
    config = load_and_extract_settings(settings_file)
    
    print("[INFO] Configuration:")
    print(f"  - Backend path: {config['llama_cpp_backend_path']}")
    print(f"  - Server port: {config['llama_server_port']}")
    print(f"  - GPU layers: {config['gpu_offload_layers']}\n")
    
    # Create loader with fallback ENABLED
    loader = LlamaModelLoader(
        models_dir=config['models_dir'],
        llama_class=config['llama_class'],
        llama_cpp_backend_path=config['llama_cpp_backend_path'],
        gpu_offload_layers=config['gpu_offload_layers'],
        port=config['llama_server_port'],
        fallback_to_llama_server=True  # ENABLED FOR THIS TEST
    )
    
    results = []
    
    for idx, (name, model_path) in enumerate(MODELS, 1):
        print(f"[{idx}/7] Testing {name}...")
        
        model_dir = config['models_dir'] / model_path
        
        if not model_dir.exists():
            print(f"      [SKIP] Model directory not found: {model_dir}")
            results.append((name, "SKIPPED", "Directory not found"))
            continue
        
        # Resolve model file
        model_file, error_msg = loader.resolve_model_file(model_path)
        if not model_file:
            print(f"      [FAIL] Failed to resolve: {error_msg}")
            results.append((name, "FAILED", error_msg))
            continue
        
        # Try to load
        try:
            result = loader.load_model_file(model_file, desired_ctx=2048)
            
            if result.success:
                backend = "llama-server" if result.used_llama_server else "llama-cpp-python"
                print(f"      [OK] Loaded with {backend}")
                results.append((name, "SUCCESS", backend))
            else:
                print(f"      [FAIL] {result.message}")
                results.append((name, "FAILED", result.message))
        except Exception as e:
            print(f"      [ERROR] {type(e).__name__}: {e}")
            results.append((name, "ERROR", str(e)))
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80 + "\n")
    
    for name, status, detail in results:
        print(f"{name:20} | {status:8} | {detail}")
    
    success_count = sum(1 for _, status, _ in results if status == "SUCCESS")
    print(f"\n[RESULT] {success_count}/{len(MODELS)} models loaded successfully")
    
    return success_count == len(MODELS)


if __name__ == "__main__":
    try:
        success = test_all_models()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n[CANCELLED] Test interrupted by user")
        sys.exit(1)

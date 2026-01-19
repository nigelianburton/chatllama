"""Test script to attempt loading all models and report which succeed/fail.

Usage:
    conda activate chatllama
    python tests/test_model_loading.py
"""

import sys
import logging
import os
from pathlib import Path
from datetime import datetime

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from chatllama_MODELS import load_and_extract_settings, ModelValidator, LlamaModelLoader

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def print_llama_diagnostics():
    """Print diagnostic info about which llama libraries are being used."""
    logger.info("\n" + "="*80)
    logger.info("LLAMA LIBRARY DIAGNOSTIC")
    logger.info("="*80)
    
    # Check environment variables
    llama_cpp_lib = os.environ.get('LLAMA_CPP_LIB', 'NOT SET')
    logger.info(f"LLAMA_CPP_LIB env var: {llama_cpp_lib}")
    
    # Check llama-cpp-python version
    try:
        import llama_cpp
        logger.info(f"llama-cpp-python version: {llama_cpp.__version__}")
        
        # Get location of llama module
        import inspect
        llama_path = inspect.getfile(llama_cpp.llama.Llama)
        logger.info(f"llama-cpp-python location: {llama_path}")
    except Exception as e:
        logger.error(f"Error getting llama-cpp-python info: {e}")
    
    # Check if C:\Llama\llama.dll exists and get its version
    llama_dll = Path("C:\\Llama\\llama.dll")
    if llama_dll.exists():
        size = llama_dll.stat().st_size
        mtime = llama_dll.stat().st_mtime
        mod_time = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"C:\\Llama\\llama.dll exists: YES ({size:,} bytes, modified {mod_time})")
    else:
        logger.warning(f"C:\\Llama\\llama.dll exists: NO")
    
    logger.info("="*80 + "\n")

def test_all_models():
    """Test loading all discovered models."""
    
    # Print diagnostics first
    print_llama_diagnostics()
    
    # Load configuration
    settings_file = PROJECT_ROOT / "config" / "settings.yml"
    config = load_and_extract_settings(settings_file)
    
    models_dir = config["models_dir"]
    settings = config["_raw_settings"]
    Llama = config["llama_class"]
    
    logger.info("=" * 80)
    logger.info(f"Testing model loading from: {models_dir}")
    logger.info("=" * 80)
    
    # Discover all models
    validator = ModelValidator(
        models_dir=models_dir,
        settings_file=settings_file,
        settings=settings,
        model_capabilities_class=None,  # Not needed for discovery
        parent_widget=None
    )
    
    models = validator.discover_models()
    logger.info(f"\nDiscovered {len(models)} models:")
    for i, model in enumerate(models, 1):
        logger.info(f"  {i}. {model}")
    
    # Create loader with fallback disabled to test llama-cpp directly
    loader = LlamaModelLoader(
        models_dir=models_dir,
        llama_class=Llama,
        gpu_offload_layers=config["gpu_offload_layers"],
        port=config["llama_server_port"],
        fallback_to_llama_server=True,  # Enable fallback to test both paths
        llama_cpp_backend_path=config["llama_cpp_backend_path"],
    )
    
    # Test each model
    results = []
    logger.info("\n" + "=" * 80)
    logger.info("TESTING MODEL LOADING")
    logger.info("=" * 80 + "\n")
    
    for i, model_path in enumerate(models, 1):
        logger.info(f"[{i}/{len(models)}] Testing: {model_path}")
        logger.info("-" * 80)
        
        try:
            # Resolve model file
            model_file, error = loader.resolve_model_file(model_path)
            if not model_file:
                logger.error(f"  ✗ FAILED - Could not resolve model file: {error}")
                results.append((model_path, False, error))
                logger.info("")
                continue
            
            logger.info(f"  Model file: {model_file.name}")
            file_size_gb = model_file.stat().st_size / (1024**3)
            logger.info(f"  File size: {file_size_gb:.2f} GB")
            
            # Attempt to load with minimal context to save memory
            result = loader.load_model_file(model_file, desired_ctx=512)
            
            if result.success:
                logger.info(f"  ✓ SUCCESS - {result.message}")
                results.append((model_path, True, "OK"))
                
                # Clean up immediately to free memory
                if result.model:
                    try:
                        del result.model
                    except Exception:
                        pass
            else:
                logger.error(f"  ✗ FAILED - {result.message}")
                if result.error:
                    logger.error(f"  Error: {result.error}")
                results.append((model_path, False, result.error or result.message))
        
        except Exception as e:
            logger.exception(f"  ✗ EXCEPTION - {e}")
            results.append((model_path, False, str(e)))
        
        logger.info("")
    
    # Summary report
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY REPORT")
    logger.info("=" * 80 + "\n")
    
    success_count = sum(1 for _, success, _ in results if success)
    fail_count = len(results) - success_count
    
    logger.info(f"Total models tested: {len(results)}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {fail_count}")
    logger.info("")
    
    if success_count > 0:
        logger.info("SUCCESSFUL MODELS:")
        logger.info("-" * 80)
        for model, success, _ in results:
            if success:
                logger.info(f"  ✓ {model}")
        logger.info("")
    
    if fail_count > 0:
        logger.info("FAILED MODELS:")
        logger.info("-" * 80)
        for model, success, error in results:
            if not success:
                logger.info(f"  ✗ {model}")
                logger.info(f"     Error: {error[:200]}...")
                logger.info("")
    
    logger.info("=" * 80)
    logger.info(f"Test complete. Success rate: {success_count}/{len(results)} ({100*success_count/len(results):.1f}%)")
    logger.info("=" * 80)
    
    return results


if __name__ == "__main__":
    try:
        results = test_all_models()
        sys.exit(0 if all(success for _, success, _ in results) else 1)
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Test failed with exception: {e}")
        sys.exit(1)

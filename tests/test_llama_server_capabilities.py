#!/usr/bin/env python3
"""
Standalone test program to evaluate llama-server.exe capabilities.

Tests what features the C:\Llama\llama-server.exe binary supports:
- Router mode (model-less startup)
- Dynamic model loading/unloading
- Standard endpoints (health, slots, models, completion)
- OpenAI-compatible endpoints

Uses the smallest available model for testing.
"""

import subprocess
import sys
import time
import requests
import json
from pathlib import Path
from typing import Optional, Dict, Any

# Configuration
LLAMA_SERVER_EXE = Path(r"C:\Llama\llama-server.exe")
TEST_PORT = 8019  # Use different port to avoid conflicts
MODELS_DIR = Path(r"D:\LLM Models")

# Test model (smallest: Qwen3-VL-4B at 2.2GB)
TEST_MODEL_DIR = MODELS_DIR / "mradermacher" / "Qwen3-VL-4B-Instruct-abliterated-v2-GGUF"


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print a section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}")


def print_test(name: str):
    """Print test name."""
    print(f"\n{Colors.BOLD}Testing: {name}{Colors.RESET}")


def print_pass(msg: str):
    """Print success message."""
    print(f"  {Colors.GREEN}✓ PASS{Colors.RESET} - {msg}")


def print_fail(msg: str):
    """Print failure message."""
    print(f"  {Colors.RED}✗ FAIL{Colors.RESET} - {msg}")


def print_info(msg: str):
    """Print info message."""
    print(f"  {Colors.YELLOW}ℹ INFO{Colors.RESET} - {msg}")


def find_model_file() -> Optional[Path]:
    """Find the test model .gguf file."""
    if not TEST_MODEL_DIR.exists():
        return None
    
    gguf_files = [f for f in TEST_MODEL_DIR.glob("*.gguf") 
                  if "mmproj" not in f.name.lower()]
    
    if not gguf_files:
        return None
    
    # Return smallest file
    return min(gguf_files, key=lambda f: f.stat().st_size)


def start_server(with_model: bool = False, model_path: Optional[Path] = None) -> Optional[subprocess.Popen]:
    """Start llama-server with or without a model.
    
    Args:
        with_model: If True, start with -m flag
        model_path: Path to model file (required if with_model=True)
    
    Returns:
        Popen object or None on failure
    """
    if not LLAMA_SERVER_EXE.exists():
        print_fail(f"llama-server.exe not found at {LLAMA_SERVER_EXE}")
        return None
    
    args = [
        str(LLAMA_SERVER_EXE),
        "--port", str(TEST_PORT),
        "-c", "2048",
        "-ngl", "10",  # Small GPU offload for testing
    ]
    
    if with_model:
        if not model_path:
            print_fail("model_path required when with_model=True")
            return None
        args.extend(["-m", str(model_path)])
    
    print_info(f"Starting server: {' '.join(args[:4])}{'...' if len(args) > 4 else ''}")
    
    try:
        proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
        
        # Wait for server to be ready
        for i in range(30):
            time.sleep(1)
            try:
                r = requests.get(f"http://localhost:{TEST_PORT}/health", timeout=1)
                if r.status_code == 200:
                    print_pass(f"Server started (health check OK after {i+1}s)")
                    return proc
            except (requests.ConnectionError, requests.Timeout):
                if i % 5 == 0 and i > 0:
                    print_info(f"Still waiting... ({i}s)")
                continue
        
        print_fail("Server failed to start within 30 seconds")
        proc.terminate()
        return None
        
    except Exception as e:
        print_fail(f"Failed to start server: {e}")
        return None


def stop_server(proc: subprocess.Popen):
    """Stop the server process."""
    if proc and proc.poll() is None:
        print_info("Stopping server...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
            print_pass("Server stopped")
        except subprocess.TimeoutExpired:
            proc.kill()
            print_info("Server killed (timeout)")


def test_endpoint(method: str, endpoint: str, data: Optional[Dict] = None, 
                  expected_codes: list = [200]) -> tuple[bool, Optional[Dict]]:
    """Test an HTTP endpoint.
    
    Returns:
        (success, response_data)
    """
    url = f"http://localhost:{TEST_PORT}{endpoint}"
    
    try:
        if method == "GET":
            r = requests.get(url, timeout=5)
        elif method == "POST":
            r = requests.post(url, json=data, timeout=5)
        else:
            return False, None
        
        success = r.status_code in expected_codes
        
        try:
            response_data = r.json()
        except:
            response_data = {"text": r.text[:200]}
        
        if success:
            print_pass(f"{method} {endpoint} → {r.status_code}")
        else:
            print_fail(f"{method} {endpoint} → {r.status_code} (expected {expected_codes})")
        
        return success, response_data
        
    except Exception as e:
        print_fail(f"{method} {endpoint} → {e}")
        return False, None


def main():
    """Run all capability tests."""
    print_header("LLAMA-SERVER CAPABILITY TEST SUITE")
    print(f"Binary: {LLAMA_SERVER_EXE}")
    print(f"Test Port: {TEST_PORT}")
    print(f"Models Dir: {MODELS_DIR}")
    
    # Find test model
    print_test("Finding test model")
    model_file = find_model_file()
    if not model_file:
        print_fail(f"No model found in {TEST_MODEL_DIR}")
        return 1
    
    model_size_mb = model_file.stat().st_size / (1024 * 1024)
    print_pass(f"Found: {model_file.name} ({model_size_mb:.1f} MB)")
    
    results = {
        "router_mode": False,
        "router_load": False,
        "router_unload": False,
        "model_mode": False,
        "health_endpoint": False,
        "slots_endpoint": False,
        "models_endpoint": False,
        "oai_chat": False,
        "native_completion": False,
    }
    
    # ========================================================================
    # TEST 1: Router Mode (model-less startup)
    # ========================================================================
    print_header("TEST 1: Router Mode (Start Without Model)")
    proc = start_server(with_model=False)
    
    if proc:
        results["router_mode"] = True
        
        # Test basic endpoints in router mode
        print_test("Health endpoint")
        success, data = test_endpoint("GET", "/health")
        results["health_endpoint"] = success
        
        print_test("Slots endpoint")
        success, data = test_endpoint("GET", "/slots")
        results["slots_endpoint"] = success
        
        print_test("Models list endpoint (GET /models)")
        success, data = test_endpoint("GET", "/models")
        if success and data:
            print_info(f"Response: {json.dumps(data, indent=2)[:200]}")
        
        print_test("Models list endpoint (GET /v1/models)")
        success, data = test_endpoint("GET", "/v1/models")
        results["models_endpoint"] = success
        if success and data:
            print_info(f"Found {len(data.get('data', []))} models")
        
        # Test dynamic model loading (router mode feature)
        print_test("Dynamic model loading (POST /models/load)")
        load_payload = {"model": str(model_file)}
        success, data = test_endpoint("POST", "/models/load", load_payload, [200, 201])
        results["router_load"] = success
        
        if success:
            print_info("Waiting 3s for model to load...")
            time.sleep(3)
            
            # Verify model loaded
            print_test("Verify model loaded (GET /v1/models)")
            success, data = test_endpoint("GET", "/v1/models")
            if success and data:
                models = data.get("data", [])
                if models:
                    print_pass(f"Model loaded: {models[0].get('id', 'unknown')}")
                else:
                    print_fail("No models reported after load")
            
            # Test chat completion with loaded model
            print_test("Chat completion with loaded model")
            chat_payload = {
                "model": "test",
                "messages": [{"role": "user", "content": "Say 'Hello'"}],
                "max_tokens": 10
            }
            success, data = test_endpoint("POST", "/v1/chat/completions", chat_payload)
            results["oai_chat"] = success
            if success and data:
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                print_info(f"Response: {content[:100]}")
            
            # Test dynamic unload
            print_test("Dynamic model unloading (POST /models/unload)")
            unload_payload = {"model": str(model_file)}
            success, data = test_endpoint("POST", "/models/unload", unload_payload, [200, 201])
            results["router_unload"] = success
        
        stop_server(proc)
        time.sleep(2)
    
    # ========================================================================
    # TEST 2: Traditional Mode (start with model via -m flag)
    # ========================================================================
    print_header("TEST 2: Traditional Mode (Start With Model)")
    proc = start_server(with_model=True, model_path=model_file)
    
    if proc:
        results["model_mode"] = True
        
        # Test if dynamic load/unload still available
        print_test("Check if /models/load available in -m mode")
        load_payload = {"model": str(model_file)}
        success, _ = test_endpoint("POST", "/models/load", load_payload, [200, 201, 404])
        if success:
            print_info("Dynamic load available even in -m mode")
        else:
            print_info("Dynamic load NOT available in -m mode (expected)")
        
        # Test completions
        print_test("Native completion endpoint")
        comp_payload = {
            "prompt": "Hello",
            "n_predict": 5,
            "stream": False
        }
        success, data = test_endpoint("POST", "/completion", comp_payload)
        results["native_completion"] = success
        if success and data:
            content = data.get("content", "")
            print_info(f"Response: {content[:100]}")
        
        print_test("OpenAI chat completion")
        chat_payload = {
            "model": "test",
            "messages": [{"role": "user", "content": "Say 'Hi'"}],
            "max_tokens": 10
        }
        success, data = test_endpoint("POST", "/v1/chat/completions", chat_payload)
        if not results["oai_chat"]:  # Only update if not already tested
            results["oai_chat"] = success
        if success and data:
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            print_info(f"Response: {content[:100]}")
        
        stop_server(proc)
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    print_header("TEST RESULTS SUMMARY")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    print(f"\n{Colors.BOLD}Overall: {passed}/{total} tests passed{Colors.RESET}\n")
    
    for test_name, passed in results.items():
        status = f"{Colors.GREEN}✓ PASS{Colors.RESET}" if passed else f"{Colors.RED}✗ FAIL{Colors.RESET}"
        print(f"  {status} - {test_name}")
    
    # ========================================================================
    # RECOMMENDATIONS
    # ========================================================================
    print_header("RECOMMENDATIONS")
    
    if results["router_mode"] and results["router_load"]:
        print(f"\n{Colors.GREEN}✓ Router mode fully supported!{Colors.RESET}")
        print("  Your llama-server supports model-less startup with dynamic loading.")
        print("  Recommended approach: Start without -m, use POST /models/load")
    elif results["router_mode"] and not results["router_load"]:
        print(f"\n{Colors.YELLOW}⚠ Partial router support{Colors.RESET}")
        print("  Server can start without model but dynamic loading not available.")
        print("  Recommended approach: Start with -m flag, restart on model change")
    elif results["model_mode"]:
        print(f"\n{Colors.YELLOW}⚠ Traditional mode only{Colors.RESET}")
        print("  Server requires -m flag at startup.")
        print("  Recommended approach: Kill + restart server when switching models")
    else:
        print(f"\n{Colors.RED}✗ Server failed to start{Colors.RESET}")
        print("  Check if llama-server.exe is valid and port is available")
    
    print()
    return 0 if passed >= total // 2 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Interrupted by user{Colors.RESET}")
        sys.exit(130)

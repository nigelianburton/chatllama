"""Test the LlamaServerClient and adapter integration"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from chatllama_llama_server import LlamaServerClient, LlamaServerAdapter


def test_llama_server_client():
    """Test LlamaServerClient connectivity and inference."""
    
    print("\n" + "="*80)
    print("TEST: LlamaServerClient Integration")
    print("="*80 + "\n")
    
    # Create client
    client = LlamaServerClient(host="localhost", port=8000)
    print(f"[INFO] Created client: {client}")
    
    # Check health
    print("\n[TEST] Checking llama-server health...")
    if client.is_alive():
        print("[OK] llama-server is alive and responding")
    else:
        print("[WARN] llama-server is not responding on port 8000")
        print("[INFO] Note: llama-server needs to be running separately")
        print("[INFO] You can start it with: & \"C:\\Llama\\llama-server.exe\" -m <model_path> --port 8000")
        return False
    
    # Test with simple message
    print("\n[TEST] Sending test message to llama-server...")
    try:
        messages = [
            {"role": "user", "content": "Say 'Hello' and nothing else."}
        ]
        
        response_text = ""
        chunk_count = 0
        
        for chunk in client.create_chat_completion(messages=messages, stream=True, max_tokens=10):
            choice = chunk.get("choices", [{}])[0]
            delta = choice.get("delta", {})
            content = delta.get("content", "")
            
            if content:
                response_text += content
                print(f"  [{chunk_count}] {repr(content)}")
                chunk_count += 1
            
            usage = chunk.get("usage")
            if usage:
                print(f"\n[INFO] Usage: prompt={usage.get('prompt_tokens')}, completion={usage.get('completion_tokens')}")
        
        print(f"\n[OK] Received {chunk_count} chunks")
        print(f"[OK] Response: {repr(response_text)}")
        
        # Test adapter
        print("\n[TEST] Testing LlamaServerAdapter...")
        adapter = LlamaServerAdapter(client)
        print(f"[OK] Adapter: {adapter}")
        print(f"[OK] Adapter.create_chat_completion exists: {hasattr(adapter, 'create_chat_completion')}")
        
        return True
        
    except Exception as e:
        print(f"\n[FAIL] Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = test_llama_server_client()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n[CANCELLED] Test interrupted")
        sys.exit(1)

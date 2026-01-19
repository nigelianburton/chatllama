"""llama-server REST API client for ChatLlama."""

import logging
import requests
import json
from typing import Generator, Dict, Any

logger = logging.getLogger(__name__)


class LlamaServerClient:
    """HTTP client for communicating with llama-server REST API."""
    
    def __init__(self, host: str = "localhost", port: int = 8000):
        """Initialize client pointing to llama-server instance.
        
        Args:
            host: Hostname of llama-server (default: localhost)
            port: Port number of llama-server (default: 8000)
        """
        self.base_url = f"http://{host}:{port}"
        self.host = host
        self.port = port
    
    def is_alive(self) -> bool:
        """Check if llama-server is running and healthy."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=1)
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"llama-server health check failed: {e}")
            return False

    def unload_model(self, model_name: str = None) -> bool:
        """Request the server to unload the currently loaded model.

        For router mode (model-less server), use POST /models/unload with model name.
        Falls back to legacy endpoints if router mode fails.
        Returns True on success.
        """
        # Try router mode endpoint first (requires model name)
        if model_name:
            router_url = f"{self.base_url}/models/unload"
            try:
                response = requests.post(router_url, json={"model": model_name}, timeout=5)
                if response.status_code == 200:
                    logger.info("llama-server: model unload requested successfully (router mode)")
                    return True
                else:
                    logger.debug("llama-server: router unload returned %s", response.status_code)
            except requests.exceptions.RequestException as e:
                logger.debug("llama-server: router unload failed: %s", e)
        
        # Fallback to legacy endpoints
        endpoints = [
            f"{self.base_url}/v1/unload",
            f"{self.base_url}/unload",
        ]
        for url in endpoints:
            try:
                response = requests.post(url, timeout=5)
                if response.status_code == 200:
                    logger.info("llama-server: model unload requested successfully (%s)", url)
                    return True
                else:
                    logger.debug("llama-server: unload endpoint %s returned %s", url, response.status_code)
            except requests.exceptions.RequestException as e:
                logger.debug("llama-server: unload request failed on %s: %s", url, e)
        return False
    
    def create_chat_completion(self, messages: list[dict], stream: bool = True, **kwargs) -> Generator[dict, None, None] | dict:
        """Create a chat completion via llama-server.
        
        Tries OpenAI-compatible endpoint first; on 404/405 falls back to
        llama.cpp native `/completion` endpoint by converting messages
        into a prompt and mapping SSE tokens to OpenAI delta chunks.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            stream: If True, yield chunks; if False, return full response
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
            
        Yields:
            For stream=True: Dict with {"choices": [{"delta": {"content": str}}]}
            For stream=False: Returns full response dict
        """
        
        # 1) Try OpenAI-compatible route first
        oai_payload = {
            "messages": messages,
            "stream": stream,
        }
        for key in ["temperature", "top_p", "max_tokens", "n", "frequency_penalty", "presence_penalty"]:
            if key in kwargs:
                oai_payload[key] = kwargs[key]
        oai_url = f"{self.base_url}/v1/chat/completions"

        try:
            if stream:
                resp = requests.post(oai_url, json=oai_payload, stream=True, timeout=3600)
                if resp.status_code in (404, 405):
                    raise requests.HTTPError(f"{resp.status_code} for OAI endpoint", response=resp)
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    line = line.decode('utf-8') if isinstance(line, bytes) else line
                    if line.startswith('data: '):
                        data = line[6:].strip()
                        if data and data != "[DONE]":
                            try:
                                chunk = json.loads(data)
                                yield chunk
                            except json.JSONDecodeError:
                                logger.warning("Failed to parse OAI chunk: %s", data)
                                continue
            else:
                resp = requests.post(oai_url, json=oai_payload, timeout=3600)
                if resp.status_code in (404, 405):
                    raise requests.HTTPError(f"{resp.status_code} for OAI endpoint", response=resp)
                resp.raise_for_status()
                yield resp.json()
                return
        except requests.HTTPError as http_err:
            # Only fallback for 404/405; otherwise re-raise
            status = getattr(http_err.response, 'status_code', None)
            if status not in (404, 405):
                logger.error("llama-server OAI request failed: %s", http_err)
                raise
            logger.info("OAI routes unavailable (%s). Falling back to /completion.", status)
        except requests.exceptions.RequestException as e:
            logger.error("llama-server OAI request failed: %s", e)
            raise

        # 2) Fallback: llama.cpp native /completion endpoint
        def _messages_to_prompt(msgs: list[dict]) -> str:
            sys_parts = []
            convo_parts = []
            for m in msgs:
                role = m.get('role', '')
                content = m.get('content', '')
                if not isinstance(content, str):
                    # Handle content as list (e.g., images); keep text-only
                    try:
                        content = ' '.join(
                            part.get('text', '') for part in content if isinstance(part, dict) and 'text' in part
                        )
                    except Exception:
                        content = str(content)
                if role == 'system' and content:
                    sys_parts.append(content)
                elif role == 'user' and content:
                    convo_parts.append(f"User: {content}")
                elif role == 'assistant' and content:
                    convo_parts.append(f"Assistant: {content}")
            sys_prompt = ("System: " + "\n\n".join(sys_parts) + "\n\n") if sys_parts else ""
            return sys_prompt + "\n".join(convo_parts) + ("\nAssistant: " if convo_parts else "")

        prompt = _messages_to_prompt(messages)
        n_predict = kwargs.get("max_tokens", kwargs.get("n_predict", 256))
        completion_payload: Dict[str, Any] = {
            "prompt": prompt,
            "stream": stream,
            "n_predict": n_predict,
        }
        if "temperature" in kwargs:
            completion_payload["temperature"] = kwargs["temperature"]
        if "top_p" in kwargs:
            completion_payload["top_p"] = kwargs["top_p"]
        # prompt cache helps speed & stability on llama.cpp server
        completion_payload["cache_prompt"] = True

        comp_url = f"{self.base_url}/completion"
        try:
            if stream:
                resp = requests.post(comp_url, json=completion_payload, stream=True, timeout=3600)
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    s = line.decode('utf-8') if isinstance(line, bytes) else line
                    if not s.startswith('data: '):
                        continue
                    data = s[6:].strip()
                    if not data or data == "[DONE]":
                        continue
                    try:
                        obj = json.loads(data)
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse /completion chunk: %s", data)
                        continue
                    # Try common fields used by llama.cpp server
                    text = ""
                    if isinstance(obj, dict):
                        if isinstance(obj.get("content"), str):
                            text = obj["content"]
                        elif isinstance(obj.get("response"), str):
                            text = obj["response"]
                        elif isinstance(obj.get("token"), dict) and isinstance(obj["token"].get("text"), str):
                            text = obj["token"]["text"]
                    if text:
                        yield {"choices": [{"delta": {"content": text}}]}
            else:
                resp = requests.post(comp_url, json=completion_payload, timeout=3600)
                resp.raise_for_status()
                obj = resp.json()
                text = obj.get("content") or obj.get("response") or ""
                yield {"choices": [{"message": {"role": "assistant", "content": text}}]}
        except requests.exceptions.RequestException as e:
            logger.error("llama-server /completion request failed: %s", e)
            raise
    
    def get_models(self) -> list[dict]:
        """Get list of models the server reports (typically the loaded model)."""
        try:
            response = requests.get(f"{self.base_url}/v1/models", timeout=5)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get models list: {e}")
            return []

    def get_loaded_model_path(self) -> str | None:
        """Best-effort extraction of currently loaded model's file path.

        Different server versions may return fields like 'id', 'name', 'path'.
        We try common keys and return the first plausible path-like string.
        """
        models = self.get_models()
        if not models:
            return None
        # Try the first entry
        entry = models[0]
        for key in ("path", "model", "file", "id", "name"):
            val = entry.get(key)
            if isinstance(val, str) and ("\\" in val or "/" in val or val.lower().endswith(".gguf")):
                return val
        return None

    def load_model(self, model_path: str, ngl: int | None = None, n_ctx: int | None = None) -> bool:
        """Request server to load a model dynamically in router mode.

        Uses POST /models/load endpoint (llama.cpp router mode).
        Returns True on success.
        """
        payload: Dict[str, Any] = {"model": model_path}
        if ngl is not None:
            payload["ngl"] = ngl
        if n_ctx is not None:
            payload["n_ctx"] = n_ctx

        # Router mode endpoint (documented in llama.cpp README)
        endpoints = [
            f"{self.base_url}/models/load",
        ]
        for url in endpoints:
            try:
                r = requests.post(url, json=payload, timeout=60)
                if r.status_code == 200:
                    logger.info("llama-server: model load requested successfully (%s)", url)
                    return True
                else:
                    logger.debug("llama-server: load endpoint %s returned %s: %s", url, r.status_code, r.text[:200])
            except requests.exceptions.RequestException as e:
                logger.debug("llama-server: load request failed on %s: %s", url, e)
        return False


# Make the client behave like a Llama object for compatibility
class LlamaServerAdapter:
    """Adapter to make LlamaServerClient compatible with Llama interface."""
    
    def __init__(self, client: LlamaServerClient):
        self.client = client
    
    def create_chat_completion(self, **kwargs) -> Generator[dict, None, None]:
        """Compatibility wrapper for create_chat_completion."""
        return self.client.create_chat_completion(**kwargs)
    
    def __repr__(self) -> str:
        return f"<LlamaServerAdapter at {self.client.base_url}>"

from __future__ import annotations

import base64
import json
import mimetypes
import sys
import urllib.error
import urllib.request
from pathlib import Path

from SIMPLE.constants import LLAMA_SERVER_HOST, LLAMA_SERVER_PORT

MODEL_ID = "Qwen3-VL-4B-Instruct-abliterated-v2.Q4_K_S"
IMAGE_PATH = Path(r"D:\_GITN\chatllama\SIMPLE\josie.png")
PROMPT = "Who is featured in this photo?"


def _url(path: str) -> str:
    return f"http://{LLAMA_SERVER_HOST}:{LLAMA_SERVER_PORT}{path}"


def _data_url(path: Path) -> str:
    data = path.read_bytes()
    mime, _ = mimetypes.guess_type(str(path))
    if not mime:
        mime = "image/png"
    encoded = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def _post_json(path: str, payload: dict, timeout: float = 60.0) -> tuple[int, str]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        _url(path),
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as err:
        return err.code, err.read().decode("utf-8")
    except Exception as exc:
        return 0, f"{type(exc).__name__}: {exc}"


def main() -> int:
    if not IMAGE_PATH.exists():
        print(f"Image not found: {IMAGE_PATH}")
        return 2

    print("Loading model...")
    status, body = _post_json("/models/load", {"model": MODEL_ID}, timeout=30)
    print(f"/models/load -> HTTP {status} {body}")

    data_url = _data_url(IMAGE_PATH)

    payloads = [
        {
            "name": "openai_content_list",
            "payload": {
                "model": MODEL_ID,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": PROMPT},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    }
                ],
                "stream": False,
            },
        },
        {
            "name": "llama_image_base64",
            "payload": {
                "model": MODEL_ID,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": PROMPT},
                            {"type": "image", "image": data_url},
                        ],
                    }
                ],
                "stream": False,
            },
        },
    ]

    for entry in payloads:
        name = entry["name"]
        payload = entry["payload"]
        print(f"\nAttempt: {name}")
        status, body = _post_json("/v1/chat/completions", payload, timeout=120)
        print(f"/v1/chat/completions -> HTTP {status}")
        print(body[:2000])

    return 0


if __name__ == "__main__":
    sys.exit(main())

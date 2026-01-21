from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Callable, Iterable, Optional

from Engine.logger import get_logger
from Engine.manager_chats import LlamaChatManager
from constants import (
    AUTORUN_BUSY_ACK_TIMEOUT_SECONDS,
    AUTORUN_READY_TIMEOUT_SECONDS,
    AUTORUN_RESPONSE_TIMEOUT_SECONDS,
)


class AutorunError(RuntimeError):
    pass


def run_autorun(
    request_args: Iterable[str],
    ui_stage_message: Optional[Callable[[str, list[Path]], None]] = None,
    ui_submit_message: Optional[Callable[[], None]] = None,
    register_availability_callback: Optional[Callable[[Callable[[str], None]], bool]] = None,
    ui_get_last_response: Optional[Callable[[], str]] = None,
) -> tuple[bool, str]:
    logger = get_logger("Autorun")
    args = list(request_args)
    if not args:
        return False, "No autorun arguments provided. Specify a text file (and optional images)."

    text_path = Path(args[0])
    if not text_path.exists():
        return False, f"Autorun file not found: {text_path}"

    if text_path.suffix.lower() != ".json":
        return False, f"Autorun now requires JSON input: {text_path}"

    try:
        payload = json.loads(text_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"Autorun JSON parse failed: {exc}"

    messages: list[dict[str, object]] = []
    if isinstance(payload, dict):
        raw_messages = payload.get("messages")
        if raw_messages is None:
            prompt = payload.get("prompt")
            if isinstance(prompt, str) and prompt.strip():
                raw_messages = [prompt]
        if isinstance(raw_messages, list):
            for item in raw_messages:
                if isinstance(item, str):
                    messages.append({"text": item, "images": []})
                elif isinstance(item, dict):
                    text = (
                        item.get("text")
                        or item.get("message")
                        or item.get("prompt")
                    )
                    if isinstance(text, str) and text.strip():
                        images = item.get("images") or []
                        if isinstance(images, str):
                            images = [images]
                        if not isinstance(images, list):
                            images = []
                        messages.append({"text": text, "images": images})
        if not messages:
            return False, f"Autorun JSON has no messages: {text_path}"
    else:
        return False, f"Autorun JSON must be an object: {text_path}"

    parsed_messages: list[tuple[str, list[Path]]] = []
    for message in messages:
        text = str(message.get("text") or "").strip()
        if not text:
            continue
        image_values = message.get("images") or []
        image_paths: list[Path] = []
        if isinstance(image_values, list):
            for item in image_values:
                if not item:
                    continue
                path = Path(str(item))
                if not path.exists():
                    return False, f"Autorun image not found: {path}"
                image_paths.append(path)
        parsed_messages.append((text, image_paths))

    if not parsed_messages:
        return False, f"Autorun file is empty: {text_path}"

    logger.info(
        "Autorun request: text=%s messages=%d",
        text_path,
        len(parsed_messages),
    )

    chat_manager: Optional[LlamaChatManager] = None
    availability_event = threading.Event()
    availability_lock = threading.Lock()
    availability_state: Optional[str] = None

    def _on_availability(state: str) -> None:
        nonlocal availability_state
        with availability_lock:
            availability_state = state
        availability_event.set()
        logger.info("Autorun availability update: %s", state)

    registered = False
    if register_availability_callback is not None:
        try:
            registered = register_availability_callback(_on_availability)
        except Exception as exc:
            logger.exception("Autorun failed to register UI availability callback: %s", exc)
            registered = False

    if not registered:
        chat_manager = LlamaChatManager()
        chat_manager.register_availability_callback(_on_availability)
        registered = True
        logger.info("Autorun availability registered via chat manager instance")
    else:
        logger.info("Autorun availability registered via UI chat manager")

    if not _wait_for_availability(
        availability_event,
        availability_lock,
        lambda: availability_state,
        "AVAILABLE",
        AUTORUN_READY_TIMEOUT_SECONDS,
    ):
        return False, "Autorun timed out waiting for chat availability."

    total = len(parsed_messages)
    for index, (line, image_paths) in enumerate(parsed_messages, start=1):
        if not _wait_for_availability(
            availability_event,
            availability_lock,
            lambda: availability_state,
            "AVAILABLE",
            AUTORUN_READY_TIMEOUT_SECONDS,
        ):
            return False, "Autorun timed out waiting for chat availability."

        logger.info("Autorun manager ready: staging line %d/%d", index, total)
        if ui_stage_message is not None:
            ui_stage_message(line, image_paths)
            logger.info("Autorun staged line %d/%d", index, total)
        else:
            logger.info("Autorun staging skipped (no UI hook) for line %d/%d", index, total)

        time.sleep(1.0)

        logger.info("Autorun submitting line %d/%d", index, total)
        if ui_submit_message is not None:
            ui_submit_message()
        elif chat_manager is not None:
            chat_manager.send_message(line, image_paths=image_paths)
        else:
            return False, "Autorun has no submit handler available."

        availability_event.clear()
        if not _wait_for_availability(
            availability_event,
            availability_lock,
            lambda: availability_state,
            "BUSY",
            AUTORUN_BUSY_ACK_TIMEOUT_SECONDS,
        ):
            return False, "Autorun expected chat to become BUSY after submit, but it did not."

        availability_event.clear()
        if not _wait_for_availability(
            availability_event,
            availability_lock,
            lambda: availability_state,
            "AVAILABLE",
            AUTORUN_RESPONSE_TIMEOUT_SECONDS,
        ):
            return False, "Autorun timed out waiting for chat response (no AVAILABLE signal)."

        response_text = ""
        if ui_get_last_response is not None:
            try:
                response_text = ui_get_last_response() or ""
            except Exception:
                response_text = ""
        if not response_text and chat_manager is not None:
            response_text = chat_manager.get_last_assistant_message()
        if response_text:
            summary = _summarize_response(response_text)
            logger.info("Autorun response summary: %s", summary)

    logger.info("Autorun completed successfully")
    return True, "Autorun completed successfully."


def _summarize_response(text: str, max_chars: int = 200) -> str:
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return ""
    split = cleaned.split(". ")
    first_sentence = split[0].strip()
    summary = first_sentence if first_sentence else cleaned
    if len(summary) > max_chars:
        return summary[: max_chars - 3].rstrip() + "..."
    return summary


def _wait_for_availability(
    event: threading.Event,
    lock: threading.Lock,
    getter: callable,
    expected: str,
    timeout: float,
) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        event.wait(timeout=0.1)
        with lock:
            state = getter()
        if state == expected:
            return True
        event.clear()
    return False

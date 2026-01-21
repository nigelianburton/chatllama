from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class InteractionEntry:
    timestamp: str
    action: str
    type: str
    content: str
    details: list[dict]
    attachments: list[str]


class InteractionLogger:
    def __init__(self, path: Path, log_file: Path) -> None:
        self._path = path
        self._log_file = log_file
        self._lock = threading.Lock()
        self._entries: list[InteractionEntry] = []
        self._session_started = datetime.now().isoformat(timespec="seconds")
        self._write()

    def log(
        self,
        message_type: str,
        content: str,
        action: str = "add",
        details: Optional[list[tuple[str, str]]] = None,
        attachments: Optional[list[Path]] = None,
    ) -> None:
        entry = InteractionEntry(
            timestamp=datetime.now().isoformat(timespec="seconds"),
            action=action,
            type=message_type,
            content=content,
            details=[{"key": key, "value": value} for key, value in (details or [])],
            attachments=[str(path) for path in (attachments or [])],
        )
        with self._lock:
            self._entries.append(entry)
            self._write()

    def _write(self) -> None:
        payload = {
            "session_started": self._session_started,
            "log_file": str(self._log_file),
            "entries": [entry.__dict__ for entry in self._entries],
        }
        self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


_interaction_logger: InteractionLogger | None = None


def init_interaction_logger(log_file: Path) -> InteractionLogger:
    global _interaction_logger
    log_path = log_file.parent / "interaction.json"
    _interaction_logger = InteractionLogger(log_path, log_file)
    return _interaction_logger


def get_interaction_logger() -> InteractionLogger | None:
    return _interaction_logger

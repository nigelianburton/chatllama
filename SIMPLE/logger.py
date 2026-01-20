from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from constants import SETTINGS_DEV


LOGS_DIR = None


@dataclass
class LogConfig:
    log_file: Path
    level: int = logging.DEBUG


def _ensure_utf8_console() -> None:
    if sys.platform == "win32":
        import io

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


class _ClassnameFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "classname"):
            record.classname = "Unknown"
        return True


class _QuietFilter(logging.Filter):
    def __init__(self, noisy_names: set[str]) -> None:
        super().__init__()
        self._noisy_names = noisy_names

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno < logging.INFO:
            if record.name in self._noisy_names or record.name == "Unknown":
                return False
        return True


class ClassLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:
        extra = kwargs.setdefault("extra", {})
        extra.setdefault("classname", self.extra.get("classname", "Unknown"))
        return msg, kwargs


class _StreamToLogger:
    def __init__(self, stream, logger: logging.Logger, level: int) -> None:
        self._stream = stream
        self._logger = logger
        self._level = level

    def write(self, message: str) -> None:
        if not message:
            return
        self._stream.write(message)
        self._stream.flush()

        stripped = message.strip()
        if not stripped:
            return
        if stripped.startswith("["):
            self._logger.log(self._level, stripped)
        else:
            self._logger.log(self._level, "[STDOUT] %s", stripped)

    def flush(self) -> None:
        self._stream.flush()

    def isatty(self) -> bool:
        return bool(getattr(self._stream, "isatty", lambda: False)())

    def fileno(self) -> int:
        return int(getattr(self._stream, "fileno", lambda: -1)())

    @property
    def encoding(self) -> str:
        return getattr(self._stream, "encoding", "utf-8")

    @property
    def errors(self) -> str:
        return getattr(self._stream, "errors", "replace")


def configure_logging(settings_folder: Path) -> LogConfig:
    logs_dir = settings_folder / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = logs_dir / f"session_{timestamp}.log"

    _ensure_utf8_console()

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(classname)s: %(message)s")

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    classname_filter = _ClassnameFilter()
    quiet_filter = _QuietFilter({"fastmcp", "mcp", "uvicorn", "pydocket", "redis", "httpx", "httpcore"})
    file_handler.addFilter(classname_filter)
    console_handler.addFilter(classname_filter)
    file_handler.addFilter(quiet_filter)
    console_handler.addFilter(quiet_filter)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    for noisy in ("fastmcp", "mcp", "uvicorn", "pydocket", "redis", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.INFO)

    stderr_logger = logging.getLogger("STDERR")
    stdout_logger = logging.getLogger("STDOUT")

    sys.stderr = _StreamToLogger(sys.stderr, stderr_logger, logging.ERROR)
    sys.stdout = _StreamToLogger(sys.stdout, stdout_logger, logging.INFO)

    def _excepthook(exc_type, exc_value, exc_traceback):
        logging.getLogger("EXCEPTION").error(
            "Unhandled exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

    sys.excepthook = _excepthook

    return LogConfig(log_file=log_file)


def get_logger(source: Any) -> ClassLoggerAdapter:
    if isinstance(source, str):
        classname = source
        name = source
    else:
        classname = getattr(source, "__name__", source.__class__.__name__)
        name = source.__class__.__name__ if not isinstance(source, type) else source.__name__

    logger = logging.getLogger(name)
    return ClassLoggerAdapter(logger, {"classname": classname})

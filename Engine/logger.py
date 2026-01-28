from __future__ import annotations

import atexit
import logging
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from constants import SETTINGS_DEV


LOGS_DIR: Path | None = None
LOG_FILE: Path | None = None
LOG_FORMATTER: logging.Formatter | None = None

NOISY_LOGGERS = {"fastmcp", "mcp", "uvicorn", "pydocket", "redis", "httpx", "httpcore"}


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


class _DowngradeSseErrors(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        if "Error in standalone SSE writer" in message or "ClosedResourceError" in message:
            record.levelno = logging.INFO
            record.levelname = "INFO"
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
        self._downgrade_sse_traceback = False

    def write(self, message: str) -> None:
        if not message:
            return
        self._stream.write(message)
        self._stream.flush()

        stripped = message.strip()
        if not stripped:
            return
        if "Error in standalone SSE writer" in stripped:
            self._downgrade_sse_traceback = True
            self._logger.log(logging.INFO, stripped)
            return
        if self._downgrade_sse_traceback:
            if stripped.startswith("Traceback") or stripped.startswith("File ") or "ClosedResourceError" in stripped:
                self._logger.log(logging.INFO, stripped)
                if "ClosedResourceError" in stripped:
                    self._downgrade_sse_traceback = False
                return
            if not stripped.startswith(" "):
                self._downgrade_sse_traceback = False
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


class _CollapsingHandler(logging.Handler):
    def __init__(self, handler: logging.Handler) -> None:
        super().__init__(handler.level)
        self._handler = handler
        self._last_record: logging.LogRecord | None = None
        self._last_key: tuple | None = None
        self._count = 0

    def emit(self, record: logging.LogRecord) -> None:
        key = (record.levelno, record.name, record.getMessage(), getattr(record, "classname", None))
        if self._last_key is None:
            self._last_key = key
            self._last_record = record
            self._count = 1
            return
        if key == self._last_key:
            self._count += 1
            return
        self._flush_last()
        self._last_key = key
        self._last_record = record
        self._count = 1

    def _flush_last(self) -> None:
        if self._last_record is None:
            return
        record = self._last_record
        if self._count > 1:
            message = record.getMessage() + f" ({self._count})"
            record = logging.makeLogRecord({**record.__dict__, "msg": message, "args": ()})
        try:
            self._handler.emit(record)
        except Exception:
            self.handleError(record)

    def flush(self) -> None:
        self._flush_last()
        self._last_record = None
        self._last_key = None
        self._count = 0
        self._handler.flush()

    def close(self) -> None:
        try:
            self.flush()
        finally:
            self._handler.close()
            super().close()


class _CallbackHandler(logging.Handler):
    def __init__(self, callback: Callable[[str], None]) -> None:
        super().__init__()
        self._callback = callback

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
            self._callback(message)
        except Exception:
            self.handleError(record)


def _build_default_filters() -> list[logging.Filter]:
    return [
        _ClassnameFilter(),
        _QuietFilter(NOISY_LOGGERS),
        _DowngradeSseErrors(),
    ]


def add_log_listener(callback: Callable[[str], None]) -> logging.Handler:
    handler = _CallbackHandler(callback)
    formatter = LOG_FORMATTER or logging.Formatter("%(asctime)s [%(levelname)s] %(classname)s: %(message)s")
    handler.setFormatter(formatter)
    for log_filter in _build_default_filters():
        handler.addFilter(log_filter)
    logging.getLogger().addHandler(handler)
    return handler


def remove_log_listener(handler: logging.Handler) -> None:
    logging.getLogger().removeHandler(handler)


def configure_logging(settings_folder: Path) -> LogConfig:
    logs_dir = settings_folder / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    session_dir = logs_dir / timestamp
    session_dir.mkdir(parents=True, exist_ok=True)
    log_file = session_dir / "session.log"

    global LOGS_DIR, LOG_FILE
    LOGS_DIR = logs_dir
    LOG_FILE = log_file

    _ensure_utf8_console()

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(classname)s: %(message)s")
    global LOG_FORMATTER
    LOG_FORMATTER = formatter

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    filters = _build_default_filters()
    collapsing_file_handler = _CollapsingHandler(file_handler)
    collapsing_console_handler = _CollapsingHandler(console_handler)

    collapsing_file_handler.setFormatter(formatter)
    collapsing_console_handler.setFormatter(formatter)

    for log_filter in filters:
        collapsing_file_handler.addFilter(log_filter)
        collapsing_console_handler.addFilter(log_filter)

    root_logger.addHandler(collapsing_file_handler)
    root_logger.addHandler(collapsing_console_handler)

    atexit.register(collapsing_file_handler.flush)
    atexit.register(collapsing_console_handler.flush)

    for noisy in NOISY_LOGGERS:
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


def get_log_dir() -> Path | None:
    if LOG_FILE is None:
        return None
    return LOG_FILE.parent


def get_logger(source: Any) -> ClassLoggerAdapter:
    if isinstance(source, str):
        classname = source
        name = source
    else:
        classname = getattr(source, "__name__", source.__class__.__name__)
        name = source.__class__.__name__ if not isinstance(source, type) else source.__name__

    logger = logging.getLogger(name)
    return ClassLoggerAdapter(logger, {"classname": classname})

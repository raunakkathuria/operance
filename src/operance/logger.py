"""Structured logging for the Phase 0A scaffold."""

from __future__ import annotations

import json
import logging
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO

from .config import LoggingSettings

_RESERVED_LOG_RECORD_KEYS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}


def _serialize(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


class JsonFormatter(logging.Formatter):
    """Render log records as compact JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        extras = {
            key: _serialize(value)
            for key, value in record.__dict__.items()
            if key not in _RESERVED_LOG_RECORD_KEYS and not key.startswith("_")
        }
        if extras:
            payload["extra"] = extras

        if record.exc_info:
            payload["exception"] = "".join(traceback.format_exception(*record.exc_info)).strip()

        return json.dumps(payload, default=_serialize, sort_keys=True)


def configure_logging(
    settings: LoggingSettings,
    stream: TextIO | None = None,
) -> logging.Logger:
    """Return a configured package logger."""

    logger = logging.getLogger("operance")
    logger.handlers.clear()
    logger.setLevel(settings.level)
    logger.propagate = False

    handler = logging.StreamHandler(stream)
    if settings.json:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))

    logger.addHandler(handler)
    return logger

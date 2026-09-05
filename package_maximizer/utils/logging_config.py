"""
Logging configuration for Package Maximizer.

Provides a single configured logger that supports both human-readable and
structured (JSON) output. Used across the CLI and web layers for consistent,
machine-parseable diagnostics.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

_DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class JsonFormatter(logging.Formatter):
    """Formatter that emits one JSON object per log record."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(
    level: str | int = "INFO",
    *,
    json_output: bool | None = None,
    stream: Any = None,
) -> logging.Logger:
    """
    Configure the root logger for Package Maximizer.

    Args:
        level: Log level name (e.g. ``"DEBUG"``) or numeric level.
        json_output: Emit JSON lines instead of plain text. Auto-detected from
            the ``PM_LOG_JSON`` environment variable when ``None``.
        stream: Output stream (defaults to ``sys.stderr``).

    Returns:
        The configured root logger.
    """
    if isinstance(level, str):
        level = logging.getLevelName(level.upper())

    if json_output is None:
        json_output = os.environ.get("PM_LOG_JSON", "false").lower() == "true"

    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(
        JsonFormatter() if json_output else logging.Formatter(_DEFAULT_FORMAT)
    )

    root = logging.getLogger()
    # Replace existing handlers to avoid duplicate output.
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    return root


def get_logger(name: str) -> logging.Logger:
    """Return a named logger under the package hierarchy."""
    return logging.getLogger(name)

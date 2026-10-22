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
from contextlib import contextmanager
from typing import Any, Generator

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


@contextmanager
def quiet_logging(level: int = logging.CRITICAL) -> Generator[None, None, None]:
    """Route diagnostics away from the terminal for the duration of a block.

    Commands that emit machine-readable output (``--output json``) promise a
    parseable document on their output stream.  Solver and library diagnostics
    are written to stderr, which Click's test runner merges into
    ``result.output`` and which combined-output consumers (``2>&1 | jq``) see
    as corruption — a ``2026-10-22 02:11:58 - ...`` log line parses as the JSON
    number ``2026`` and breaks the document.

    Raising the global disable threshold keeps those records off the terminal
    without touching the JSON on stdout.  Text output is unaffected, so
    operators keep their diagnostics by not asking for JSON.

    Args:
        level: records at or below this level are dropped (default: all).
    """
    logging.disable(level)
    try:
        yield
    finally:
        logging.disable(logging.NOTSET)

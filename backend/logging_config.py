"""
logging_config.py — Structured JSON logging for production.

In development (LOG_FORMAT=text) outputs human-readable lines.
In production (LOG_FORMAT=json) outputs one JSON object per line,
compatible with Datadog, Loki, CloudWatch, etc.
"""

from __future__ import annotations

import json
import logging
import os
import time


class _JSONFormatter(logging.Formatter):
    """Emit one JSON object per log record."""

    def format(self, record: logging.LogRecord) -> str:
        obj: dict = {
            "ts":      time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level":   record.levelname,
            "logger":  record.name,
            "msg":     record.getMessage(),
        }
        if record.exc_info:
            obj["exc"] = self.formatException(record.exc_info)
        # Include any extra fields passed to logger.info(..., extra={...})
        for key, val in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "message",
                "taskName",
            }:
                obj[key] = val
        return json.dumps(obj, default=str)


def configure_logging(level: str = "INFO", fmt: str = "text") -> None:
    """
    Set up root logger.

    Parameters
    ----------
    level:
        Standard Python log level name.
    fmt:
        ``"json"`` for machine-readable, ``"text"`` for human-readable.
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    handler = logging.StreamHandler()
    if fmt.lower() == "json":
        handler.setFormatter(_JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            fmt="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
            datefmt="%H:%M:%S",
        ))
    root.handlers = [handler]


def setup_from_env() -> None:
    """Initialise logging from LOG_LEVEL and LOG_FORMAT environment variables."""
    configure_logging(
        level=os.getenv("LOG_LEVEL", "INFO"),
        fmt=os.getenv("LOG_FORMAT", "text"),
    )

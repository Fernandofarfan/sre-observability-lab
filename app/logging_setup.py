"""Structured logging setup: JSON logs on stdout for log aggregation."""

import json
import logging
import sys
from datetime import UTC, datetime

import structlog


class _JsonFormatter(logging.Formatter):
    """Render stdlib log records (uvicorn) as single-line JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """Render a log record as a JSON document.

        Args:
            record: The stdlib log record.

        Returns:
            A single-line JSON string.
        """
        payload: dict[str, str] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC)
            .isoformat()
            .replace("+00:00", "Z"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "event": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def _configure_uvicorn_logging(level: int) -> None:
    """Route uvicorn's stdlib loggers through the JSON formatter on stdout.

    Uvicorn installs its own handlers (startup logs on stderr, access logs on
    stdout) before importing the ASGI app, so re-pointing them here at app
    import time makes every log line structured JSON on a single stream.

    Args:
        level: Numeric stdlib log level.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = [handler]
        uvicorn_logger.propagate = False
        uvicorn_logger.setLevel(level)


def configure_logging(level: str = "INFO") -> None:
    """Configure structlog to render JSON logs to stdout.

    JSON output makes logs consumable by Loki/Promtail (or any log
    aggregator) and keeps every log line self-describing with timestamp,
    log level and structured context.

    Args:
        level: Log level name (e.g. "INFO", "DEBUG").
    """
    log_level = logging.getLevelNamesMapping().get(level.upper(), logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )
    _configure_uvicorn_logging(log_level)

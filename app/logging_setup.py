"""Structured logging setup: JSON logs on stdout for log aggregation."""

import logging
import sys

import structlog


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

"""Tests for the structured logging configuration."""

import json
import logging
import sys

from app.logging_setup import _JsonFormatter


def test_json_formatter_renders_single_line_json() -> None:
    """Verify uvicorn records become single-line JSON with the expected fields."""
    record = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='%s - "%s %s" %s',
        args=("127.0.0.1:1234", "GET", "/healthz HTTP/1.1", 200),
        exc_info=None,
    )
    payload = json.loads(_JsonFormatter().format(record))
    assert payload["level"] == "info"
    assert payload["logger"] == "uvicorn.access"
    assert payload["event"] == '127.0.0.1:1234 - "GET /healthz HTTP/1.1" 200'
    assert payload["timestamp"].endswith("Z")


def test_json_formatter_includes_traceback() -> None:
    """Verify records with exception info carry the formatted traceback."""
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        exc_info = sys.exc_info()
    record = logging.LogRecord(
        name="uvicorn.error",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="unhandled failure",
        args=None,
        exc_info=exc_info,
    )
    payload = json.loads(_JsonFormatter().format(record))
    assert payload["level"] == "error"
    assert "RuntimeError: boom" in payload["exception"]

"""Tests for OpenTelemetry telemetry setup."""

from unittest.mock import patch

import pytest
from fastapi import FastAPI

from app import telemetry
from app.config import settings

_OTLP_EXPORTER = "opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter"


def test_setup_telemetry_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """OTEL_TRACES_EXPORTER=none configures a provider without an OTLP exporter."""
    monkeypatch.setattr(settings, "OTEL_TRACES_EXPORTER", "none")
    telemetry._PROVIDER = None

    with patch(_OTLP_EXPORTER) as exporter_cls:
        telemetry.setup_telemetry(FastAPI())

    exporter_cls.assert_not_called()
    assert telemetry._PROVIDER is not None


def test_setup_telemetry_otlp(monkeypatch: pytest.MonkeyPatch) -> None:
    """OTLP mode wires the exporter to the configured collector endpoint."""
    monkeypatch.setattr(settings, "OTEL_TRACES_EXPORTER", "otlp")
    telemetry._PROVIDER = None

    with patch(_OTLP_EXPORTER) as exporter_cls:
        telemetry.setup_telemetry(FastAPI())

    exporter_cls.assert_called_once_with(
        endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        insecure=True,
    )
    assert telemetry._PROVIDER is not None

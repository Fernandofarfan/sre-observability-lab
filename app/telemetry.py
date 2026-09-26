"""OpenTelemetry instrumentation and tracing setup."""

import structlog
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider

from app.config import settings

logger = structlog.get_logger()

_RESOURCE = Resource.create(
    {
        SERVICE_NAME: settings.SERVICE_NAME,
        SERVICE_VERSION: settings.SERVICE_VERSION,
        "deployment.environment": settings.ENVIRONMENT,
    }
)

_PROVIDER: TracerProvider | None = None


def setup_telemetry(app: FastAPI) -> None:
    """Initialize OpenTelemetry tracing and instrument FastAPI.

    Spans are exported via OTLP/gRPC to the configured collector endpoint
    (the OTel Collector forwards them to Jaeger). Set
    OTEL_TRACES_EXPORTER=none to disable export entirely, which is useful
    in CI or local runs without a collector.

    Args:
        app: The FastAPI application instance to instrument.
    """
    global _PROVIDER  # noqa: PLW0603

    _PROVIDER = TracerProvider(resource=_RESOURCE)

    if settings.OTEL_TRACES_EXPORTER.lower() == "none":
        logger.info(
            "telemetry_configured",
            exporter="none",
            note="OTLP export disabled via OTEL_TRACES_EXPORTER",
        )
    else:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        exporter = OTLPSpanExporter(
            endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
            insecure=True,
        )
        _PROVIDER.add_span_processor(BatchSpanProcessor(exporter))
        logger.info(
            "telemetry_configured",
            exporter="otlp",
            endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        )

    trace.set_tracer_provider(_PROVIDER)
    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()

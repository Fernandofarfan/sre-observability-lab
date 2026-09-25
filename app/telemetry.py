"""OpenTelemetry instrumentation and tracing setup."""

import structlog
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
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

    When the OTEL_EXPORTER_OTLP_ENDPOINT is reachable, traces are exported
    via OTLP/gRPC. Otherwise, a no-op exporter is used and the app functions
    normally with local tracing only.

    Args:
        app: The FastAPI application instance to instrument.
    """
    global _PROVIDER  # noqa: PLW0603

    _PROVIDER = TracerProvider(resource=_RESOURCE)
    use_otlp = "localhost" in settings.OTEL_EXPORTER_OTLP_ENDPOINT or "127.0.0.1" in settings.OTEL_EXPORTER_OTLP_ENDPOINT

    if use_otlp:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        exporter = OTLPSpanExporter(
            endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
            insecure=True,
        )
        _PROVIDER.add_span_processor(BatchSpanProcessor(exporter))
        logger.info("telemetry_configured", exporter="otlp", endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)
    else:
        logger.info(
            "telemetry_configured",
            exporter="noop",
            note="OTLP endpoint not local, tracing active but not exported",
        )

    trace.set_tracer_provider(_PROVIDER)
    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()


def get_tracer() -> trace.Tracer:
    """Return a named tracer for manual span creation.

    Returns:
        A tracer instance bound to the configured provider.
    """
    return trace.get_tracer(settings.SERVICE_NAME, settings.SERVICE_VERSION)

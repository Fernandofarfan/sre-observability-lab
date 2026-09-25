"""SRE Observability Lab - FastAPI application entry point."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from prometheus_client import make_asgi_app

from app.config import settings
from app.middleware import PrometheusMiddleware
from app.routes import chaos, health, orders
from app.telemetry import setup_telemetry

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201
    """Application lifespan handler: initialise telemetry on startup."""
    setup_telemetry(app)
    logger.info(
        "service_started",
        service=settings.SERVICE_NAME,
        version=settings.SERVICE_VERSION,
        environment=settings.ENVIRONMENT,
    )
    yield
    logger.info("service_stopped", service=settings.SERVICE_NAME)


app = FastAPI(
    title=settings.SERVICE_NAME,
    version=settings.SERVICE_VERSION,
    lifespan=lifespan,
)

app.add_middleware(PrometheusMiddleware)

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

app.include_router(health.router)
app.include_router(orders.router)
app.include_router(chaos.router)


@app.get("/")
async def root() -> dict[str, str]:
    """Return service metadata.

    Returns:
        JSON with service name, version and status.
    """
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "status": "operational",
    }

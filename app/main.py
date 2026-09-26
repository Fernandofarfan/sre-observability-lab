"""SRE Observability Lab - FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from app.config import settings
from app.logging_setup import configure_logging
from app.middleware import PrometheusMiddleware
from app.routes import chaos, health, orders
from app.telemetry import setup_telemetry

configure_logging(settings.LOG_LEVEL)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
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


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log unhandled exceptions as structured JSON before returning a generic 500.

    Args:
        request: The request that triggered the exception.
        exc: The unhandled exception.

    Returns:
        A generic 500 JSON response.
    """
    logger.error(
        "unhandled_exception",
        method=request.method,
        path=request.url.path,
        error=repr(exc),
        exc_info=True,
    )
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

"""Health-check and service info endpoints."""

import time

from fastapi import APIRouter
from opentelemetry import trace

from app.config import APP_START_TIME, settings

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def liveness() -> dict[str, str]:
    """Liveness probe - always returns alive.

    Returns:
        JSON indicating the service is alive.
    """
    return {"status": "alive"}


@router.get("/readyz")
async def readiness() -> dict[str, str]:
    """Readiness probe - verifies telemetry provider is available.

    Returns:
        JSON indicating the service is ready.

    Raises:
        503: If the tracer provider is not initialised.
    """
    provider = trace.get_tracer_provider()
    if provider is None:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=503, content={"status": "not ready"})
    return {"status": "ready"}


@router.get("/info")
async def info() -> dict[str, str | float]:
    """Return service metadata including uptime.

    Returns:
        JSON with service name, version, environment and uptime in seconds.
    """
    uptime = time.time() - APP_START_TIME
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "environment": settings.ENVIRONMENT,
        "uptime_seconds": round(uptime, 2),
    }

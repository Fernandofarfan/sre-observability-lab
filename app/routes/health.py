"""Health-check and service info endpoints."""

import time

from fastapi import APIRouter, HTTPException
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

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
    """Readiness probe - verifies telemetry is initialised.

    The lifespan handler installs a real TracerProvider on startup; until
    that happens the API returns 503 so load balancers do not route traffic
    to an instance that cannot serve traces.

    Returns:
        JSON indicating the service is ready.

    Raises:
        503: If the tracer provider has not been installed yet.
    """
    if not isinstance(trace.get_tracer_provider(), TracerProvider):
        raise HTTPException(status_code=503, detail="telemetry not initialised")
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

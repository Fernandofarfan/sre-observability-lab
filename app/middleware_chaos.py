"""Chaos engineering dependency for business endpoints."""

import asyncio
import random

from fastapi import HTTPException, Request

from app.config import settings
from app.routes.chaos import chaos_state


async def chaos_dependency(request: Request) -> None:
    """Dependency that applies chaos injection to business endpoints.

    Checks the global chaos state and, if enabled, injects artificial
    latency or errors before the endpoint handler executes. Injection is
    skipped entirely when CHAOS_ENABLED is false.

    Args:
        request: The incoming FastAPI request.

    Raises:
        HTTPException: With status 500 when error injection triggers.
    """
    path = request.url.path
    if not path.startswith("/api/v1/") or not settings.CHAOS_ENABLED:
        return

    if chaos_state.latency.enabled:
        delay_ms = random.randint(chaos_state.latency.min_ms, chaos_state.latency.max_ms)
        await asyncio.sleep(delay_ms / 1000.0)

    if chaos_state.errors.enabled and random.random() < chaos_state.errors.rate:
        raise HTTPException(
            status_code=500,
            detail="Chaos-injected internal error",
        )

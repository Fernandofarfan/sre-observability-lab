"""Chaos engineering endpoints for runtime fault injection."""

import hmac

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, model_validator

from app.config import settings

logger = structlog.get_logger()

router = APIRouter(prefix="/chaos", tags=["chaos"])


class ChaosLatencyConfig(BaseModel):
    """Schema for latency injection configuration."""

    enabled: bool
    min_ms: int = Field(default=0, ge=0)
    max_ms: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _validate_range(self) -> "ChaosLatencyConfig":
        """Reject an inverted range, which would crash random.randint at request time.

        Returns:
            The validated configuration.

        Raises:
            ValueError: If latency is enabled and min_ms exceeds max_ms.
        """
        if self.enabled and self.min_ms > self.max_ms:
            raise ValueError("min_ms must be <= max_ms when latency injection is enabled")
        return self


class ChaosErrorConfig(BaseModel):
    """Schema for error injection configuration."""

    enabled: bool
    rate: float = Field(default=0.0, ge=0.0, le=1.0)


class ChaosState:
    """Mutable container for chaos injection settings."""

    def __init__(self) -> None:
        """Initialise chaos state with defaults."""
        self.latency = ChaosLatencyConfig(enabled=False, min_ms=0, max_ms=0)
        self.errors = ChaosErrorConfig(enabled=False, rate=0.0)


chaos_state = ChaosState()


class ChaosStatusResponse(BaseModel):
    """Schema for the chaos status response."""

    latency: ChaosLatencyConfig
    errors: ChaosErrorConfig


async def require_chaos_enabled(request: Request) -> None:
    """Guard for chaos mutation endpoints.

    Enforces the CHAOS_ENABLED setting and, when CHAOS_TOKEN is set,
    requires a matching X-Chaos-Token header.

    Args:
        request: The incoming FastAPI request.

    Raises:
        403: If chaos injection is disabled via CHAOS_ENABLED.
        401: If CHAOS_TOKEN is set and the header is missing or wrong.
    """
    if not settings.CHAOS_ENABLED:
        raise HTTPException(
            status_code=403, detail="Chaos injection disabled (CHAOS_ENABLED=false)"
        )
    if settings.CHAOS_TOKEN:
        provided = request.headers.get("X-Chaos-Token", "")
        if not hmac.compare_digest(provided, settings.CHAOS_TOKEN):
            raise HTTPException(status_code=401, detail="Missing or invalid X-Chaos-Token header")


@router.post("/latency", dependencies=[Depends(require_chaos_enabled)])
async def configure_latency(config: ChaosLatencyConfig) -> ChaosLatencyConfig:
    """Enable or disable artificial latency injection.

    Args:
        config: Latency configuration with enabled flag and millisecond range.

    Returns:
        The updated latency configuration.
    """
    chaos_state.latency = config
    logger.info(
        "chaos_latency_updated",
        enabled=config.enabled,
        min_ms=config.min_ms,
        max_ms=config.max_ms,
    )
    return config


@router.post("/errors", dependencies=[Depends(require_chaos_enabled)])
async def configure_errors(config: ChaosErrorConfig) -> ChaosErrorConfig:
    """Enable or disable artificial error rate injection.

    Args:
        config: Error configuration with enabled flag and rate (0.0-1.0).

    Returns:
        The updated error configuration.
    """
    chaos_state.errors = config
    logger.info("chaos_errors_updated", enabled=config.enabled, rate=config.rate)
    return config


@router.get("/status", response_model=ChaosStatusResponse)
async def chaos_status() -> ChaosStatusResponse:
    """Return the current chaos injection state.

    Returns:
        Current latency and error injection settings.
    """
    return ChaosStatusResponse(latency=chaos_state.latency, errors=chaos_state.errors)


@router.post("/reset", dependencies=[Depends(require_chaos_enabled)])
async def reset_chaos() -> dict[str, str]:
    """Disable all chaos injection and reset to defaults.

    Returns:
        Confirmation message.
    """
    chaos_state.latency = ChaosLatencyConfig(enabled=False, min_ms=0, max_ms=0)
    chaos_state.errors = ChaosErrorConfig(enabled=False, rate=0.0)
    logger.info("chaos_reset")
    return {"status": "chaos_reset"}

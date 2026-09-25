"""Chaos engineering endpoints for runtime fault injection."""

import structlog
from fastapi import APIRouter
from pydantic import BaseModel

logger = structlog.get_logger()

router = APIRouter(prefix="/chaos", tags=["chaos"])


class ChaosLatencyConfig(BaseModel):
    """Schema for latency injection configuration."""

    enabled: bool
    min_ms: int = 0
    max_ms: int = 0


class ChaosErrorConfig(BaseModel):
    """Schema for error injection configuration."""

    enabled: bool
    rate: float = 0.0


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


@router.post("/latency")
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


@router.post("/errors")
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


@router.post("/reset")
async def reset_chaos() -> dict[str, str]:
    """Disable all chaos injection and reset to defaults.

    Returns:
        Confirmation message.
    """
    chaos_state.latency = ChaosLatencyConfig(enabled=False, min_ms=0, max_ms=0)
    chaos_state.errors = ChaosErrorConfig(enabled=False, rate=0.0)
    logger.info("chaos_reset")
    return {"status": "chaos_reset"}

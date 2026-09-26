"""Tests for the application lifespan handler."""

import pytest

from app import main as main_module


@pytest.mark.asyncio
async def test_lifespan_initialises_telemetry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify startup initialises telemetry and shutdown completes cleanly."""
    initialised: list[object] = []
    monkeypatch.setattr(main_module, "setup_telemetry", initialised.append)

    async with main_module.lifespan(main_module.app):
        assert initialised == [main_module.app]

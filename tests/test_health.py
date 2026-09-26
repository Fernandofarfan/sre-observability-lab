"""Tests for health-check endpoints."""

import httpx
import pytest

from app.routes import health as health_module


@pytest.mark.asyncio
async def test_liveness(client: httpx.AsyncClient) -> None:
    """Verify /healthz returns alive status."""
    response = await client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"


@pytest.mark.asyncio
async def test_readiness(client: httpx.AsyncClient) -> None:
    """Verify /readyz returns ready status."""
    response = await client.get("/readyz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"


@pytest.mark.asyncio
async def test_readiness_503_when_telemetry_missing(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify /readyz returns 503 when no real TracerProvider is installed."""

    class _UninitialisedProvider:
        pass

    monkeypatch.setattr(health_module, "TracerProvider", _UninitialisedProvider)
    response = await client.get("/readyz")
    assert response.status_code == 503
    assert response.json()["detail"] == "telemetry not initialised"


@pytest.mark.asyncio
async def test_info(client: httpx.AsyncClient) -> None:
    """Verify /info returns service metadata."""
    response = await client.get("/info")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "sre-observability-lab"
    assert data["version"] == "1.0.0"
    assert data["environment"] == "development"
    assert "uptime_seconds" in data


@pytest.mark.asyncio
async def test_root(client: httpx.AsyncClient) -> None:
    """Verify root endpoint returns service info."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "sre-observability-lab"
    assert data["version"] == "1.0.0"
    assert data["status"] == "operational"

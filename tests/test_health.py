"""Tests for health-check endpoints."""

import httpx
import pytest


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

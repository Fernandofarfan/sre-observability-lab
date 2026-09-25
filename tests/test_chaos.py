"""Tests for chaos engineering endpoints."""

import httpx
import pytest


@pytest.mark.asyncio
async def test_configure_latency(client: httpx.AsyncClient) -> None:
    """Verify POST /chaos/latency enables latency injection."""
    payload = {"enabled": True, "min_ms": 100, "max_ms": 500}
    response = await client.post("/chaos/latency", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is True
    assert data["min_ms"] == 100
    assert data["max_ms"] == 500


@pytest.mark.asyncio
async def test_configure_errors(client: httpx.AsyncClient) -> None:
    """Verify POST /chaos/errors enables error injection."""
    payload = {"enabled": True, "rate": 0.25}
    response = await client.post("/chaos/errors", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is True
    assert data["rate"] == 0.25


@pytest.mark.asyncio
async def test_chaos_status(client: httpx.AsyncClient) -> None:
    """Verify GET /chaos/status returns current chaos configuration."""
    await client.post("/chaos/latency", json={"enabled": True, "min_ms": 50, "max_ms": 200})
    await client.post("/chaos/errors", json={"enabled": True, "rate": 0.1})

    response = await client.get("/chaos/status")
    assert response.status_code == 200
    data = response.json()
    assert "latency" in data
    assert "errors" in data
    assert data["latency"]["enabled"] is True
    assert data["latency"]["min_ms"] == 50
    assert data["latency"]["max_ms"] == 200
    assert data["errors"]["enabled"] is True
    assert data["errors"]["rate"] == 0.1


@pytest.mark.asyncio
async def test_reset_chaos(client: httpx.AsyncClient) -> None:
    """Verify POST /chaos/reset disables all chaos injection."""
    await client.post("/chaos/latency", json={"enabled": True, "min_ms": 300, "max_ms": 800})
    await client.post("/chaos/errors", json={"enabled": True, "rate": 0.5})

    response = await client.post("/chaos/reset")
    assert response.status_code == 200
    assert response.json()["status"] == "chaos_reset"

    status_resp = await client.get("/chaos/status")
    status = status_resp.json()
    assert status["latency"]["enabled"] is False
    assert status["latency"]["min_ms"] == 0
    assert status["latency"]["max_ms"] == 0
    assert status["errors"]["enabled"] is False
    assert status["errors"]["rate"] == 0.0


@pytest.mark.asyncio
async def test_chaos_error_injection_on_order(client: httpx.AsyncClient) -> None:
    """Verify chaos error injection triggers 500 on business endpoints."""
    await client.post("/chaos/errors", json={"enabled": True, "rate": 1.0})

    payload = {
        "customer_id": "cust-chaos-test",
        "items": [{"product_id": "prod-001", "quantity": 1, "price": 10.00}],
    }
    response = await client.post("/api/v1/orders", json=payload)
    assert response.status_code == 500
    assert response.json()["detail"] == "Chaos-injected internal error"

    await client.post("/chaos/reset")

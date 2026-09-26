"""Tests for chaos engineering endpoints."""

import time

import httpx
import pytest

from app.config import settings


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


@pytest.mark.asyncio
async def test_chaos_disabled_returns_403(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify mutation endpoints are blocked when CHAOS_ENABLED is false."""
    monkeypatch.setattr(settings, "CHAOS_ENABLED", False)

    response = await client.post(
        "/chaos/latency", json={"enabled": True, "min_ms": 10, "max_ms": 20}
    )
    assert response.status_code == 403
    assert "disabled" in response.json()["detail"]

    status = await client.get("/chaos/status")
    assert status.status_code == 200


@pytest.mark.asyncio
async def test_chaos_requires_token_when_configured(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify X-Chaos-Token is enforced when CHAOS_TOKEN is set."""
    monkeypatch.setattr(settings, "CHAOS_TOKEN", "s3cret-token")

    missing = await client.post("/chaos/errors", json={"enabled": True, "rate": 0.1})
    assert missing.status_code == 401

    wrong = await client.post(
        "/chaos/errors",
        json={"enabled": True, "rate": 0.1},
        headers={"X-Chaos-Token": "wrong"},
    )
    assert wrong.status_code == 401

    ok = await client.post(
        "/chaos/errors",
        json={"enabled": True, "rate": 0.1},
        headers={"X-Chaos-Token": "s3cret-token"},
    )
    assert ok.status_code == 200

    await client.post("/chaos/reset", headers={"X-Chaos-Token": "s3cret-token"})
    monkeypatch.setattr(settings, "CHAOS_TOKEN", "")


@pytest.mark.asyncio
async def test_chaos_skipped_when_disabled_on_business_endpoint(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify no errors are injected into business endpoints when chaos is disabled."""
    await client.post("/chaos/errors", json={"enabled": True, "rate": 1.0})
    monkeypatch.setattr(settings, "CHAOS_ENABLED", False)

    payload = {
        "customer_id": "cust-disabled-test",
        "items": [{"product_id": "prod-001", "quantity": 1, "price": 10.00}],
    }
    response = await client.post("/api/v1/orders", json=payload)
    assert response.status_code == 201

    monkeypatch.setattr(settings, "CHAOS_ENABLED", True)
    await client.post("/chaos/reset")


@pytest.mark.asyncio
async def test_latency_rejects_inverted_range(client: httpx.AsyncClient) -> None:
    """Verify an enabled latency range with min_ms > max_ms is rejected with 422."""
    response = await client.post(
        "/chaos/latency", json={"enabled": True, "min_ms": 5000, "max_ms": 10}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_latency_allows_inverted_range_when_disabled(client: httpx.AsyncClient) -> None:
    """Verify range ordering is only enforced while latency injection is enabled."""
    response = await client.post(
        "/chaos/latency", json={"enabled": False, "min_ms": 5000, "max_ms": 10}
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_latency_rejects_negative_values(client: httpx.AsyncClient) -> None:
    """Verify negative millisecond values are rejected with 422."""
    response = await client.post(
        "/chaos/latency", json={"enabled": True, "min_ms": -1, "max_ms": 100}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chaos_errors_rejects_rate_out_of_range(client: httpx.AsyncClient) -> None:
    """Verify error rates outside [0.0, 1.0] are rejected with 422."""
    for rate in (-0.1, 1.5):
        response = await client.post("/chaos/errors", json={"enabled": True, "rate": rate})
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_latency_injection_delays_business_requests(client: httpx.AsyncClient) -> None:
    """Verify enabled latency injection actually delays business requests."""
    await client.post("/chaos/latency", json={"enabled": True, "min_ms": 50, "max_ms": 50})

    payload = {
        "customer_id": "cust-latency-test",
        "items": [{"product_id": "prod-001", "quantity": 1, "price": 10.00}],
    }
    start = time.perf_counter()
    response = await client.post("/api/v1/orders", json=payload)
    elapsed = time.perf_counter() - start

    assert response.status_code == 201
    assert elapsed >= 0.05

    await client.post("/chaos/reset")

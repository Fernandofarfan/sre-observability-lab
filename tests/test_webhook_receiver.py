"""Tests for the Alertmanager webhook receiver."""

import httpx
import pytest

from app.webhook_receiver.main import app as receiver_app


@pytest.fixture
async def receiver_client() -> httpx.AsyncClient:
    """Create an async HTTP client for testing the webhook receiver app.

    Returns:
        An httpx.AsyncClient wired to the receiver app via ASGITransport.
    """
    transport = httpx.ASGITransport(app=receiver_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.mark.asyncio
async def test_healthz(receiver_client: httpx.AsyncClient) -> None:
    """Verify /healthz returns alive status."""
    response = await receiver_client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


@pytest.mark.asyncio
async def test_receive_alert_payload(receiver_client: httpx.AsyncClient) -> None:
    """Verify an Alertmanager payload is accepted, counted and exposed."""
    payload = {
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {"alertname": "ErrorBudgetBurnRate_Fast", "severity": "critical"},
                "annotations": {"summary": "Fast burn detected"},
            },
            {
                "status": "resolved",
                "labels": {"alertname": "ErrorBudgetBurnRate_Fast", "severity": "critical"},
                "annotations": {},
            },
        ],
    }
    response = await receiver_client.post("/pager", json=payload)
    assert response.status_code == 200
    assert response.json() == {"received": 2}

    metrics = await receiver_client.get("/metrics/")
    assert metrics.status_code == 200
    assert (
        'alerts_received_total{alertname="ErrorBudgetBurnRate_Fast",'
        'receiver="pager",severity="critical",status="firing"}' in metrics.text
    )


@pytest.mark.asyncio
async def test_invalid_json_returns_400(receiver_client: httpx.AsyncClient) -> None:
    """Verify a non-JSON body is rejected with 400."""
    response = await receiver_client.post(
        "/", content="not-json", headers={"content-type": "application/json"}
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_non_alertmanager_payload_returns_502(receiver_client: httpx.AsyncClient) -> None:
    """Verify JSON without an alerts field is rejected with 502."""
    response = await receiver_client.post("/", json={"foo": "bar"})
    assert response.status_code == 502

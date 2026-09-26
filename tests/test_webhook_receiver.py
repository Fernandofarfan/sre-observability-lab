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


@pytest.mark.asyncio
async def test_unknown_label_values_are_bounded(receiver_client: httpx.AsyncClient) -> None:
    """Verify arbitrary alertname/severity/status never become metric label values.

    The receiver listens on the published host port, so unbounded label
    values would allow anyone to create unlimited time series.
    """
    payload = {
        "status": "weird-status",
        "alerts": [
            {
                "status": "weird-status",
                "labels": {"alertname": f"evil-{'x' * 200}", "severity": "banana"},
                "annotations": {},
            }
        ],
    }
    response = await receiver_client.post("/", json=payload)
    assert response.status_code == 200

    metrics = await receiver_client.get("/metrics/")
    body = metrics.text
    assert 'alerts_received_total{alertname="other",' in body
    assert 'severity="other"' in body
    assert 'status="other"' in body
    assert "evil-" not in body
    assert "banana" not in body


@pytest.mark.asyncio
async def test_ticket_receiver_ingests_alert(receiver_client: httpx.AsyncClient) -> None:
    """Verify warning-severity alerts routed to the ticket receiver are counted."""
    payload = {
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {"alertname": "HighLatency_P95", "severity": "warning"},
                "annotations": {},
            }
        ],
    }
    response = await receiver_client.post("/ticket", json=payload)
    assert response.status_code == 200
    assert response.json() == {"received": 1}

    metrics = await receiver_client.get("/metrics/")
    assert 'receiver="ticket"' in metrics.text
    assert 'alertname="HighLatency_P95"' in metrics.text


@pytest.mark.asyncio
async def test_malformed_alert_entries_are_skipped(receiver_client: httpx.AsyncClient) -> None:
    """Verify non-dict alerts and non-dict labels are handled without error."""
    payload = {
        "status": "firing",
        "alerts": [
            "not-a-dict",
            {"status": "firing", "labels": "not-a-dict"},
        ],
    }
    response = await receiver_client.post("/", json=payload)
    assert response.status_code == 200
    assert response.json() == {"received": 1}

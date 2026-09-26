"""Tests for Prometheus metrics middleware behaviour."""

import httpx
import pytest
from fastapi import FastAPI

from app.middleware import (
    HTTP_REQUESTS_IN_PROGRESS,
    HTTP_REQUESTS_TOTAL,
    PrometheusMiddleware,
)


async def test_endpoint_label_uses_route_template(client: httpx.AsyncClient) -> None:
    """Verify metric labels use the route template, not the raw URL path.

    Guards against metric cardinality explosion: a request to
    /api/v1/orders/<uuid> must be recorded under
    /api/v1/orders/{order_id}, and the raw uuid must never appear as a
    label value.
    """
    create_payload = {
        "customer_id": "cust-metrics-test",
        "items": [{"product_id": "prod-001", "quantity": 1, "price": 5.00}],
    }
    create_resp = await client.post("/api/v1/orders", json=create_payload)
    assert create_resp.status_code == 201
    order_id = create_resp.json()["order_id"]

    get_resp = await client.get(f"/api/v1/orders/{order_id}")
    assert get_resp.status_code == 200

    metrics_resp = await client.get("/metrics/")
    assert metrics_resp.status_code == 200
    body = metrics_resp.text

    assert 'endpoint="/api/v1/orders/{order_id}"' in body
    assert 'endpoint="/api/v1/orders"' in body
    assert order_id not in body


@pytest.mark.asyncio
async def test_unmatched_paths_aggregated(client: httpx.AsyncClient) -> None:
    """Verify requests to unknown routes are aggregated under 'unmatched'."""
    response = await client.get("/definitely/not/a/route")
    assert response.status_code == 404

    metrics_resp = await client.get("/metrics/")
    assert 'endpoint="unmatched"' in metrics_resp.text


@pytest.mark.asyncio
async def test_exception_records_500_and_releases_gauge() -> None:
    """Verify a failing request records a 500 and releases the in-flight gauge."""
    failing_app = FastAPI()
    failing_app.add_middleware(PrometheusMiddleware)

    @failing_app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("boom")

    transport = httpx.ASGITransport(app=failing_app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
        response = await ac.get("/boom")

    assert response.status_code == 500
    assert HTTP_REQUESTS_IN_PROGRESS.labels(method="GET")._value.get() == 0
    counter = HTTP_REQUESTS_TOTAL.labels(method="GET", endpoint="/boom", status_code="500")
    assert counter._value.get() >= 1

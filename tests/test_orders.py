"""Tests for order management endpoints."""

import httpx
import pytest


@pytest.mark.asyncio
async def test_create_order(client: httpx.AsyncClient) -> None:
    """Verify POST /api/v1/orders creates an order successfully."""
    payload = {
        "customer_id": "cust-test-001",
        "items": [
            {"product_id": "prod-001", "quantity": 2, "price": 29.99},
            {"product_id": "prod-002", "quantity": 1, "price": 49.99},
        ],
    }
    response = await client.post("/api/v1/orders", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "order_id" in data
    assert data["customer_id"] == "cust-test-001"
    assert data["total"] == 109.97
    assert data["status"] == "confirmed"
    assert "created_at" in data
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_get_existing_order(client: httpx.AsyncClient) -> None:
    """Verify GET /api/v1/orders/{id} returns an existing order."""
    create_payload = {
        "customer_id": "cust-test-002",
        "items": [{"product_id": "prod-010", "quantity": 1, "price": 15.00}],
    }
    create_resp = await client.post("/api/v1/orders", json=create_payload)
    assert create_resp.status_code == 201
    order_id = create_resp.json()["order_id"]

    get_resp = await client.get(f"/api/v1/orders/{order_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["order_id"] == order_id
    assert data["customer_id"] == "cust-test-002"
    assert data["total"] == 15.00


@pytest.mark.asyncio
async def test_get_nonexistent_order(client: httpx.AsyncClient) -> None:
    """Verify GET /api/v1/orders/{id} returns 404 for unknown order."""
    response = await client.get("/api/v1/orders/nonexistent-id")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Order not found"


@pytest.mark.asyncio
async def test_list_orders(client: httpx.AsyncClient) -> None:
    """Verify GET /api/v1/orders returns a list of orders."""
    response = await client.get("/api/v1/orders")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    for order in data:
        assert "order_id" in order
        assert "customer_id" in order
        assert "total" in order
        assert "status" in order

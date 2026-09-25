"""Order service - business logic for order creation and retrieval."""

import asyncio
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import structlog
from opentelemetry import trace

from app.services.payment_service import process_payment

logger = structlog.get_logger()

_tracer = trace.get_tracer("order-service")


@dataclass
class OrderItem:
    """Represents a single item in an order."""

    product_id: str
    quantity: int
    price: float


@dataclass
class Order:
    """Represents a complete order."""

    order_id: str
    customer_id: str
    items: list[OrderItem] = field(default_factory=list)
    total: float = 0.0
    status: str = "pending"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


orders_db: dict[str, Order] = {}


async def create_order(customer_id: str, items: list[OrderItem]) -> Order:
    """Create a new order and process payment.

    Args:
        customer_id: Identifier of the customer placing the order.
        items: List of items to include in the order.

    Returns:
        The created Order with status 'confirmed'.
    """
    with _tracer.start_as_current_span("order.create") as span:
        order_id = str(uuid.uuid4())
        span.set_attribute("order.id", order_id)
        span.set_attribute("order.customer_id", customer_id)
        span.set_attribute("order.item_count", len(items))

        total = sum(item.quantity * item.price for item in items)
        span.set_attribute("order.total", total)

        order = Order(
            order_id=order_id,
            customer_id=customer_id,
            items=items,
            total=total,
            status="pending",
        )

        await process_payment(order_id, total)

        order.status = "confirmed"
        orders_db[order_id] = order

        span.set_attribute("order.status", "confirmed")
        logger.info("order_created", order_id=order_id, total=total, customer_id=customer_id)

        return order


def get_order(order_id: str) -> Order | None:
    """Retrieve an order by ID.

    Args:
        order_id: The UUID of the order.

    Returns:
        The Order if found, otherwise None.
    """
    return orders_db.get(order_id)


def list_orders() -> list[Order]:
    """List all stored orders.

    Returns:
        List of all orders.
    """
    return list(orders_db.values())

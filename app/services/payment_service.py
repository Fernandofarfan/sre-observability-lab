"""Payment service - simulated external payment gateway."""

import asyncio
import random
import uuid

import structlog
from opentelemetry import trace

logger = structlog.get_logger()

_tracer = trace.get_tracer("payment-service")


async def process_payment(order_id: str, amount: float) -> dict[str, str]:
    """Simulate processing a payment through an external gateway.

    Args:
        order_id: The order identifier to associate with the payment.
        amount: The total amount to charge.

    Returns:
        Dictionary with payment_id and approval status.
    """
    with _tracer.start_as_current_span("payment.process") as span:
        span.set_attribute("payment.order_id", order_id)
        span.set_attribute("payment.amount", amount)

        delay = random.uniform(0.01, 0.08)
        await asyncio.sleep(delay)

        payment_id = str(uuid.uuid4())
        span.set_attribute("payment.id", payment_id)
        span.set_attribute("payment.status", "approved")

        logger.info(
            "payment_processed",
            payment_id=payment_id,
            order_id=order_id,
            amount=amount,
        )

        return {"payment_id": payment_id, "status": "approved"}

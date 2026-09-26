"""Order management endpoints for simulated e-commerce flow."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.middleware_chaos import chaos_dependency
from app.services.order_service import OrderItem, create_order, get_order, list_orders

router = APIRouter(
    prefix="/api/v1/orders",
    tags=["orders"],
    dependencies=[Depends(chaos_dependency)],
)


class ItemPayload(BaseModel):
    """Schema for a single order item."""

    product_id: str
    quantity: int
    price: float


class CreateOrderRequest(BaseModel):
    """Schema for the create-order request body."""

    customer_id: str
    items: list[ItemPayload]


class OrderResponse(BaseModel):
    """Schema for an order response."""

    order_id: str
    customer_id: str
    items: list[ItemPayload]
    total: float
    status: str
    created_at: str


@router.post("", status_code=201)
async def create_order_endpoint(request: CreateOrderRequest) -> OrderResponse:
    """Create a new order.

    Args:
        request: The order creation payload.

    Returns:
        The created order with a generated UUID.
    """
    order_items = [
        OrderItem(
            product_id=item.product_id,
            quantity=item.quantity,
            price=item.price,
        )
        for item in request.items
    ]
    order = await create_order(request.customer_id, order_items)
    return OrderResponse(
        order_id=order.order_id,
        customer_id=order.customer_id,
        items=[
            ItemPayload(
                product_id=i.product_id,
                quantity=i.quantity,
                price=i.price,
            )
            for i in order.items
        ],
        total=order.total,
        status=order.status,
        created_at=order.created_at.isoformat(),
    )


@router.get("/{order_id}")
async def get_order_endpoint(order_id: str) -> OrderResponse:
    """Retrieve an order by its ID.

    Args:
        order_id: The UUID of the order.

    Returns:
        The matching order.

    Raises:
        404: If the order does not exist.
    """
    order = get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderResponse(
        order_id=order.order_id,
        customer_id=order.customer_id,
        items=[
            ItemPayload(
                product_id=i.product_id,
                quantity=i.quantity,
                price=i.price,
            )
            for i in order.items
        ],
        total=order.total,
        status=order.status,
        created_at=order.created_at.isoformat(),
    )


@router.get("")
async def list_orders_endpoint() -> list[OrderResponse]:
    """List all orders.

    Returns:
        List of all stored orders.
    """
    orders = list_orders()
    return [
        OrderResponse(
            order_id=o.order_id,
            customer_id=o.customer_id,
            items=[
                ItemPayload(
                    product_id=i.product_id,
                    quantity=i.quantity,
                    price=i.price,
                )
                for i in o.items
            ],
            total=o.total,
            status=o.status,
            created_at=o.created_at.isoformat(),
        )
        for o in orders
    ]

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class OrderItemSummary:
    product_id: int
    product_name: str
    unit_price: Decimal
    quantity: int


@dataclass(frozen=True, slots=True)
class OrderSummary:
    id: int
    user_id: int
    courier_id: int | None
    total_price: Decimal
    delivery_status: str
    payment_method: str
    payment_status: str
    created_at: datetime
    items: list[OrderItemSummary]

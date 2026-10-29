from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class RegisteredOrderItem:
    id: int
    order_id: int
    product_id: int
    product_name: str
    unit_price: Decimal
    quantity: Decimal

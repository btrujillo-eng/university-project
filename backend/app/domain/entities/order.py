from dataclasses import dataclass
from decimal import Decimal

from app.domain.enums import DeliveryStatus


@dataclass(frozen=True, slots=True)
class Order:
    user_id: int
    payment_id: int
    total_price: Decimal
    delivery_status: DeliveryStatus
    shipping_street: str
    shipping_details: str
    shipping_city: str
    phone_number: str

from dataclasses import dataclass
from decimal import Decimal

from app.domain.enums import DeliveryStatus, PaymentMethods, PaymentStatus


@dataclass(frozen=True, slots=True)
class Order:
    user_id: int
    total_price: Decimal
    payment_method: PaymentMethods
    payment_status: PaymentStatus
    delivery_status: DeliveryStatus
    shipping_street: str
    shipping_details: str
    shipping_city: str
    phone_number: str

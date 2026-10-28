from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.domain.enums import DeliveryStatus, PaymentMethods, PaymentStatus


class OrderItemResponse(BaseModel):
    product_id: int
    product_name: str
    unit_price: Decimal
    quantity: int


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    courier_id: int | None
    total_price: Decimal
    delivery_status: DeliveryStatus
    payment_method: PaymentMethods
    payment_status: PaymentStatus
    created_at: datetime
    items: list[OrderItemResponse]


class CashPaymentUpdateRequest(BaseModel):
    payment_status: PaymentStatus

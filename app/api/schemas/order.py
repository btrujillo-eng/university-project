from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.payment import PaymentMethodRequest, PaymentResponse
from app.domain.enums import DeliveryStatus, PaymentMethods, PaymentStatus


class ShippingAddressRequest(BaseModel):
    street: str = Field(min_length=4, max_length=80)
    details: str = Field(min_length=1, max_length=120)
    city: str = Field(min_length=2, max_length=60)
    phone_number: str = Field(pattern=r"^\d{10}$")


class CheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shipping: ShippingAddressRequest
    payment_method: PaymentMethodRequest
    discount_type: str = "no_aplica"


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


class DigitalReceiptResponse(BaseModel):
    receipt_number: str
    order_id: int
    issued_at: datetime
    total_paid: Decimal
    currency: str = "COP"
    items: list[OrderItemResponse]


class CheckoutResponse(BaseModel):
    order: OrderResponse
    payment: PaymentResponse
    receipt: DigitalReceiptResponse | None = None

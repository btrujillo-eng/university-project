from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.payment import PaymentMethodRequest, PaymentResponse
from app.domain.enums import DeliveryStatus, PaymentMethods, PaymentStatus


class ShippingAddressRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    street: str = Field(min_length=4, max_length=80)
    neighborhood: str = Field(min_length=2, max_length=60)
    department: str = Field(min_length=2, max_length=60)
    details: str = Field(min_length=1, max_length=120, description="Referencias adicionales del domicilio")
    delivery_instructions: str | None = Field(default=None, max_length=250)
    city: str = Field(min_length=2, max_length=60)
    phone_number: str = Field(pattern=r"^\d{10}$")


class CheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shipping: ShippingAddressRequest
    payment_method: PaymentMethodRequest


class CourierOptionResponse(BaseModel):
    id: int
    first_name: str
    first_surname: str


class OrderItemResponse(BaseModel):
    product_id: int
    product_name: str
    unit_price: Decimal
    quantity: Decimal
    image_path: str | None = None


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    customer_name: str = ""
    courier_id: int | None
    total_price: Decimal
    subtotal: Decimal
    shipping_cost: Decimal
    delivery_status: DeliveryStatus
    payment_method: PaymentMethods
    payment_status: PaymentStatus
    created_at: datetime
    shipping_street: str
    shipping_neighborhood: str
    shipping_department: str
    shipping_details: str
    shipping_instructions: str | None = None
    shipping_city: str
    phone_number: str
    items: list[OrderItemResponse]


class DeliveryStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delivery_status: DeliveryStatus


class CashPaymentUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payment_status: PaymentStatus


class DigitalReceiptResponse(BaseModel):
    receipt_number: str
    order_id: int
    issued_at: datetime
    customer_name: str
    customer_email: str
    shipping_street: str
    shipping_neighborhood: str
    shipping_department: str
    shipping_details: str
    shipping_instructions: str | None = None
    shipping_city: str
    phone_number: str
    payment_method: PaymentMethods
    total_paid: Decimal
    subtotal: Decimal
    shipping_cost: Decimal
    currency: str = "COP"
    items: list[OrderItemResponse]


class CheckoutResponse(BaseModel):
    order: OrderResponse
    payment: PaymentResponse
    receipt: DigitalReceiptResponse | None = None

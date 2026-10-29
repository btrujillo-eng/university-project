from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.api.schemas.user import UserDataRequest
from app.domain.enums import DiscountStrategy, PaymentMethods, TypeCurrency

TransactionAmount = Annotated[Decimal, Field(gt=0, decimal_places=2)]
Currency = Annotated[TypeCurrency, Field(description="Currency code")]
Message = Annotated[str, Field(description="Message with payment information")]


class CashPaymentDataRequest(BaseModel):
    method: Literal[PaymentMethods.CASH]


class CardPaymentDataRequest(BaseModel):
    method: Literal[PaymentMethods.CARD]
    payment_method_id: str = Field(
        min_length=4,
        max_length=100,
        pattern=r"^pm_[A-Za-z0-9_]+$",
        description="Stripe PaymentMethod ID created securely by Stripe.js; never send raw card details",
    )


PaymentMethodRequest = Annotated[
    CashPaymentDataRequest | CardPaymentDataRequest,
    Field(discriminator="method", description="Specific information about the payment method"),
]


class PaymentDataRequest(BaseModel):
    user_data: UserDataRequest = Field(description="User's information")
    currency: Currency = TypeCurrency.COP
    discount_type: DiscountStrategy = Field(
        default=DiscountStrategy.NODISCOUNT,
        description="Discount strategy supported by the application",
    )
    transaction_amount: Annotated[TransactionAmount, Field(description="Total payment amount")]
    payment_method: PaymentMethodRequest


class CardPaymentResponse(BaseModel):
    method: Literal[PaymentMethods.CARD]
    processing_network: str = Field(description="Card network reported by Stripe")
    last_digits: str | None = Field(default=None, min_length=4, max_length=4, pattern=r"^\d{4}$")


class CashPaymentResponse(BaseModel):
    method: Literal[PaymentMethods.CASH]


PaymentMethodResponse = Annotated[
    CardPaymentResponse | CashPaymentResponse,
    Field(discriminator="method", description="Payment method used"),
]


class PaymentResponse(BaseModel):
    currency: Currency = TypeCurrency.COP
    transaction_amount: Annotated[TransactionAmount, Field(description="Charged amount")]
    transaction_id: str = Field(description="Transaction ID")
    payment_status: str = Field(description="Payment status")
    message: Message | None = None
    created_at: datetime = Field(description="Transaction timestamp")
    payment_method: PaymentMethodResponse

import asyncio
import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import stripe
from stripe import StripeError

from app.api.schemas import (
    CardPaymentDataRequest,
    CardPaymentResponse,
    PaymentDataRequest,
    PaymentResponse,
)
from app.domain.ports import IPaymentGateway

logger = logging.getLogger(__name__)


class StripeGateway(IPaymentGateway):
    """Stripe PaymentIntent gateway.

    Card details must be tokenized in the browser with Stripe.js. The API accepts
    only a Stripe PaymentMethod ID and never receives the PAN or CVC.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def process_payment(self, payment_data: PaymentDataRequest) -> PaymentResponse:
        stripe.api_key = self.api_key
        amount = int((payment_data.transaction_amount * Decimal("100")).quantize(Decimal("1")))
        if not isinstance(payment_data.payment_method, CardPaymentDataRequest):
            raise ValueError("The payment method must be 'card'")

        payment_method_id = payment_data.payment_method.payment_method_id
        card_brand = "unknown"
        last_digits = None
        try:
            # Retrieve card metadata before charging, so a metadata lookup failure
            # cannot happen after a successful charge and before order persistence.
            method = await asyncio.to_thread(stripe.PaymentMethod.retrieve, payment_method_id)
            card = method.get("card") or {}
            if not card.get("last4") or not card.get("brand"):
                raise ValueError("The Stripe PaymentMethod is not a card")
            card_brand = str(card["brand"]).title()
            last_digits = str(card["last4"])

            intent = await asyncio.to_thread(
                stripe.PaymentIntent.create,
                amount=amount,
                currency=payment_data.currency.value,
                payment_method=payment_method_id,
                confirm=True,
                description=(
                    f"Charge for {payment_data.user_data.first_name} "
                    f"{payment_data.user_data.first_surname}"
                ),
                metadata={"integration": "canasta_express"},
            )
            succeeded = intent["status"] == "succeeded"
            return PaymentResponse(
                currency=payment_data.currency,
                transaction_amount=Decimal(intent["amount"]) / Decimal("100"),
                transaction_id=intent["id"],
                payment_status="succeeded" if succeeded else "failed",
                message="Pago exitoso" if succeeded else "El pago no pudo completarse",
                created_at=datetime.fromtimestamp(intent["created"], tz=UTC),
                payment_method=CardPaymentResponse(
                    method=payment_data.payment_method.method,
                    processing_network=card_brand,
                    last_digits=last_digits,
                ),
            )
        except StripeError as exc:
            logger.error("Stripe transaction failed: %s", exc, exc_info=True)
            return PaymentResponse(
                currency=payment_data.currency,
                transaction_amount=payment_data.transaction_amount,
                transaction_id=str(uuid4()),
                payment_status="failed",
                message="No fue posible procesar el pago. Verifica el método de pago e intenta nuevamente.",
                created_at=datetime.now(tz=UTC),
                payment_method=CardPaymentResponse(
                    method=payment_data.payment_method.method,
                    processing_network=card_brand,
                    last_digits=last_digits,
                ),
            )

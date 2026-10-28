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
from app.domain.card_utils import get_processing_network
from app.domain.constants import STRIPE_TRIAL_TOKENS
from app.domain.enums import PaymentMethods
from app.domain.payment_utils import to_stripe_amount
from app.domain.ports import IPaymentGateway
from app.exceptions import (
    StripeNetworkNotSupportError,
    StripePaymentMethodError,
    StripeTokenConfigurationError,
)

logger = logging.getLogger(__name__)


class StripeGateway(IPaymentGateway):
    """Gateway for Stripe card charges."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def process_payment(self, payment_data: PaymentDataRequest) -> PaymentResponse:
        stripe.api_key = self.api_key
        amount = to_stripe_amount(payment_data.transaction_amount)
        if not isinstance(payment_data.payment_method, CardPaymentDataRequest):
            logger.critical("The payment method must be 'tarjeta'")
            raise StripePaymentMethodError("The payment method must be 'tarjeta'")

        card_number = payment_data.payment_method.card_number.get_secret_value()
        source = get_processing_network(card_number)
        if not source:
            raise StripeNetworkNotSupportError(
                "The entered processing network has no support"
            )

        # Demo tokens must be replaced with Stripe.js tokenization in production.
        token_source = STRIPE_TRIAL_TOKENS.get(source)
        if not token_source:
            raise StripeTokenConfigurationError(
                "The processing network exists, but it does not have an assigned token"
            )

        try:
            # The Stripe SDK call is synchronous. Run it in a worker thread so it
            # does not block FastAPI's event loop while waiting for the network.
            charge = await asyncio.to_thread(
                stripe.Charge.create,
                amount=amount,
                currency=payment_data.currency.value,
                source=token_source,
                description=(
                    f"Charge for {payment_data.user_data.first_name} "
                    f"{payment_data.user_data.first_surname}"
                ),
            )
            charge_status = charge["status"]
            return PaymentResponse(
                currency=charge["currency"],
                transaction_amount=Decimal(charge["amount"]) / Decimal("100"),
                transaction_id=charge["id"],
                payment_status=charge_status,
                message="Pago exitoso" if charge_status == "succeeded" else "Pago fallido",
                created_at=datetime.fromtimestamp(charge["created"], tz=UTC),
                payment_method=CardPaymentResponse(
                    method=PaymentMethods.CARD,
                    processing_network=source,
                    last_digits=card_number[-4:],
                ),
            )
        except StripeError as exc:
            logger.error(
                "Stripe transaction failed for user %s: %s",
                payment_data.user_data.first_name,
                exc,
                exc_info=True,
            )
            return PaymentResponse(
                currency=payment_data.currency,
                transaction_amount=payment_data.transaction_amount,
                transaction_id=str(uuid4()),
                payment_status="failed",
                message=(
                    "Estamos teniendo problemas para procesar el pago. "
                    "Por favor intenta nuevamente"
                ),
                created_at=datetime.now(tz=UTC),
                payment_method=CardPaymentResponse(
                    method=PaymentMethods.CARD,
                    processing_network=source,
                    last_digits=card_number[-4:],
                ),
            )

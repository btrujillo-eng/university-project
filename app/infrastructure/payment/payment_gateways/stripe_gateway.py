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
    """
    This is a Stripe payment gateway.
    
    It is responsible for payment processing and returning the payment details. Any 
    class that implement this payment gateway can define the 'process_payment' method.
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        
    async def process_payment(self, payment_data: PaymentDataRequest) -> PaymentResponse:
        """
        It's responsible for processing a payment and returning the payment details.
        """
        stripe.api_key = self.api_key
        amount = to_stripe_amount(payment_data.transaction_amount)
        if not isinstance(payment_data.payment_method, CardPaymentDataRequest):
            logger.critical("The payment method must b  e 'tarjeta'")
            raise StripePaymentMethodError("The payment method must be 'tarjeta'")
        
        source = get_processing_network(payment_data.payment_method.card_number.get_secret_value())
        if not source:
            raise StripeNetworkNotSupportError("The entered processing network has no support")
        
        # NOTE: In a real production environment the codig lines between 36 and 38 must be removed.
        # Because the token must be assigned from the front-end by Stripe.js.
        tok_source = STRIPE_TRIAL_TOKENS.get(source)
        if not tok_source:
            raise StripeTokenConfigurationError("The processing network exists, but it does not have an assigned token")
        
        try:
            charge = stripe.Charge.create(
                amount=amount,
                currency=payment_data.currency.value,
                source=tok_source,
                description=f"Charge for {payment_data.user_data.first_name} {payment_data.user_data.first_surname}"
            )
            logger.info(f"Payment processed successfully| Transaction id: {charge["id"]}")
            return PaymentResponse(
                currency=charge["currency"],
                transaction_amount=Decimal(charge["amount"] / 100),
                transaction_id=charge["id"],
                payment_status=charge["status"],
                message="Pago exitoso" if charge["status"] == 'succeeded' else 'Pago fallido',
                created_at=datetime.fromtimestamp(charge["created"], tz=UTC),
                payment_method=CardPaymentResponse(
                    method=PaymentMethods.CARD,
                    processing_network=source,
                    last_digits=payment_data.payment_method.card_number.get_secret_value()[-4:]
                )
            )
             
        except StripeError as e:
            logger.critical(f"The transaction failed for {payment_data.user_data.first_name} | Error: {e}", stack_info=True)
            return PaymentResponse(
                currency=payment_data.currency,
                transaction_amount=payment_data.transaction_amount,
                transaction_id=str(uuid4()),
                payment_status="failed",
                message="Estamos teniendo problemas para procesar el pago. Por favor intenta nuevamente",
                created_at=datetime.now(tz=UTC),
                payment_method=CardPaymentResponse(
                    method=PaymentMethods.CARD,
                    processing_network=source,
                    last_digits=payment_data.payment_method.card_number.get_secret_value()[:4]
                )
            )
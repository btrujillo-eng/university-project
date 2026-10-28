import logging
from datetime import UTC, datetime
from uuid import uuid4

from app.api.schemas.payment import (
    CashPaymentResponse,
    PaymentDataRequest,
    PaymentResponse,
)
from app.domain.enums import PaymentMethods
from app.domain.ports import IPaymentGateway

logger = logging.getLogger(__name__)

class CashGateway(IPaymentGateway):
    async def process_payment(self, payment_data: PaymentDataRequest) -> PaymentResponse:
        transaction_id = str(uuid4())
        logger.info("Payment processed successfully | Transaction ID: %s", transaction_id)
        
        return PaymentResponse(
            currency=payment_data.currency,
            transaction_amount=payment_data.transaction_amount,
            transaction_id=transaction_id,
            payment_status="succeeded",
            message="Pago exitoso",
            created_at=datetime.now(tz=UTC),
            payment_method=CashPaymentResponse(
                method=PaymentMethods.CASH
            )
        )
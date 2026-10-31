import logging

from app.api.schemas import PaymentDataRequest, PaymentResponse
from app.domain.enums import PaymentMethods, PaymentStatus
from app.domain.ports import IOutboxRepository, IPaymentMethodFactory, IShoppingCart

logger = logging.getLogger(__name__)


class ProcessPaymentUseCase:
    def __init__(
        self,
        shopping_cart: IShoppingCart,
        payment_method_factory: IPaymentMethodFactory,
        outbox_repository: IOutboxRepository,
    ) -> None:
        self.shopping_cart = shopping_cart
        self.payment_method_factory = payment_method_factory
        self.outbox_repository = outbox_repository

    async def process(self, payment_data: PaymentDataRequest) -> PaymentResponse:
        """Process a payment and enqueue a confirmation email after card approval."""
        total_amount = self.shopping_cart.calculate_total(
            payment_data.transaction_amount,
            payment_data.discount_type,
        )
        data = payment_data.model_copy(update={"transaction_amount": total_amount})
        payment_processor = self.payment_method_factory.create_payment_processor(
            data.payment_method.method
        )
        payment_response = await payment_processor.process(data)

        if (
            payment_response.payment_method.method == PaymentMethods.CARD
            and payment_response.payment_status == PaymentStatus.SUCCEDED.value
        ):
            card_data = payment_response.payment_method
            payload = {
                "email": str(data.user_data.contact_info.email),
                "first_name": data.user_data.first_name,
                "transaction_id": payment_response.transaction_id,
                "amount": str(payment_response.transaction_amount),
                "currency": payment_response.currency.value,
                "created_at": payment_response.created_at.isoformat(),
                "processing_network": card_data.processing_network,
                "last_digits": card_data.last_digits,
            }
            try:
                await self.outbox_repository.enqueue(
                    event_key=f"payment-confirmation:{payment_response.transaction_id}",
                    event_type="payment.card.succeeded",
                    payload=payload,
                )
            except Exception:
                # Stripe has already approved the charge. Do not misreport it as failed.
                logger.exception(
                    "Payment %s succeeded but its confirmation could not be queued",
                    payment_response.transaction_id,
                )
        return payment_response

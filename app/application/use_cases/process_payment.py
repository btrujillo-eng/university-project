import logging

from app.api.schemas import PaymentDataRequest, PaymentResponse
from app.exceptions import NotificationServiceError
from app.domain.enums import PaymentMethods
from app.domain.ports import INotificationService, IPaymentMethodFactory, IShoppingCart

logger = logging.getLogger(__name__)


class ProcessPaymentUseCase:
    def __init__(
        self,
        shopping_cart: IShoppingCart,
        payment_method_factory: IPaymentMethodFactory,
        notification_service: INotificationService,
    ) -> None:
        self.shopping_cart = shopping_cart
        self.payment_method_factory = payment_method_factory
        self.notification_service = notification_service

    async def process(self, payment_data: PaymentDataRequest) -> PaymentResponse:
        total_amount = self.shopping_cart.calculate_total(
            payment_data.transaction_amount,
            payment_data.discount_type,
        )
        data = payment_data.model_copy(update={"transaction_amount": total_amount})
        payment_processor = self.payment_method_factory.create_payment_processor(
            data.payment_method.method,
        )
        payment_response = await payment_processor.process(data)
        if (
            payment_response.payment_method.method == PaymentMethods.CARD
            and payment_response.payment_status == "succeeded"
        ):
            try:
                self.notification_service.notify_all(payment_response, data)
            except Exception:
                # A notification failure must never turn a successful charge into
                # an API failure; callers could otherwise retry and be charged twice.
                logger.exception("Payment succeeded but customer notification failed")
        return payment_response

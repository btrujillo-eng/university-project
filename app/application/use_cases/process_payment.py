from app.api.schemas import PaymentDataRequest, PaymentResponse
from app.domain.enums import PaymentMethods
from app.domain.ports import INotificationService, IPaymentMethodFactory, IShoppingCart


class ProcessPaymentUseCase:
    def __init__(
            self,
            shopping_cart: IShoppingCart,
            payment_method_factory: IPaymentMethodFactory,
            notification_service: INotificationService
        ) -> None:
        self.shopping_cart = shopping_cart
        self.payment_method_factory = payment_method_factory
        self.notification_service = notification_service

    async def process(self, payment_data: PaymentDataRequest) -> PaymentResponse:
        """Create a payment processor"""
        total_amount = self.shopping_cart.calculate_total(payment_data.transaction_amount, payment_data.discount_type)
        payment_data = PaymentDataRequest(
            user_data=payment_data.user_data,
            currency=payment_data.currency,
            discount_type=payment_data.discount_type,
            transaction_amount=total_amount,
            payment_method=payment_data.payment_method
        )
        data = payment_data.model_copy(update={"transaction_amount": total_amount})
        payment_processor = self.payment_method_factory.create_payment_processor(data.payment_method.method)
        payment_response = await payment_processor.process(data)
        if payment_response.payment_method.method == PaymentMethods.CARD:
            self.notification_service.notify_all(payment_response, payment_data)
        return payment_response
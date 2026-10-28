import logging
from typing import Any

from app.domain.enums import PaymentMethods
from app.domain.ports import IPaymentMethodFactory, IPaymentProcessor

logger = logging.getLogger(__name__)

class PaymentMethodFactory(IPaymentMethodFactory):
    """
    This class is a factory of payment methods.
    
    Any class that implement this factory must defined
    the method 'create_payment_procesor.
    
    Methods:

        create_payment_processor(type_payment_method: PaymentMethods | str) -> IPaymentPocessor
        
            Create a payment processor based on the payment method.
    """
    def __init__(
            self,
            card_method: IPaymentProcessor,
            cash_method: IPaymentProcessor
            ):
        self.payment_methods: dict[Any, IPaymentProcessor] = {
            PaymentMethods.CARD: card_method,
            PaymentMethods.CASH: cash_method
        }
        
    def create_payment_processor(self, payment_method: PaymentMethods) -> IPaymentProcessor:
        """
            Create a payment processor based on the payment method.
            """
        processor_class = self.payment_methods.get(payment_method)
            
        if not processor_class:
            logger.warning(
                f"The payment method '{payment_method}' is supported by the system, "
                "but a processor has not been implemented in the factory"
            )
            raise RuntimeError(
                f"The payment method '{payment_method}' is supported by the system, "
                "but a processor has not been implemented in the factory"
            )
        return processor_class
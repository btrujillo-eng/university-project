from abc import ABC, abstractmethod
from decimal import Decimal

from app.api.schemas import PaymentDataRequest, PaymentResponse
from app.domain.enums import DiscountStrategy, PaymentMethods


class IDiscountStrategy(ABC):
    """
    Interface for applying discounts to purchases.
    
    Any class that implement this interface must define the
    method 'apply_discount'.
    
    IMPORTANT!:
        Implementations of this interface should only return the 
        discount value.
    
    Methods:
        apply_discount(payment_amount: Decimal) -> Decimal:
            Returns the discount value.
    """
    @abstractmethod
    def apply_discount(self, payment_amount: Decimal) -> Decimal: ...
          
class IShoppingCart(ABC):
    """
    Interface for a shopping cart.
    
    Any class that implement this interface must define the method 'calculate_total'.
    
    Methods:
        calculate_total(payment_amount: Decimal, discount_type: DiscountStrategy | str) -> PaymentAmountModel:
            Apply a discount type to the purchase and calculate the total price.
    """
    @abstractmethod
    def calculate_total(self, payment_amount: Decimal, discount_type: DiscountStrategy | str) -> Decimal: ...

class IPaymentGateway(ABC):
    """
    Interface for payment gateways.
    
    Any class that implement this interface must define the method 'process_payment'.
    
    Methods:
        process_payment(payment_data: BasePaymentData) -> PaymentResponse:
            It's responsible for processing a payment and returning the payment details.
    """
    @abstractmethod
    async def process_payment(self, payment_data: PaymentDataRequest) -> PaymentResponse: ...

class IPaymentProcessor(ABC):
    """
    Interface for payment processor.
    
    Any class that implement this interface must define
    the method 'process'.
    
    Methods:
        process(payment_data: BasePaymentData) -> PaymentResponse:
            processes payments with a predetermined payment method.
    """
    @abstractmethod
    async def process(self, payment_data: PaymentDataRequest) -> PaymentResponse: ...
    
class IPaymentMethodFactory(ABC):
    """
    This is a interface for factory of payment methods.
    
    Any class that implement this interface must defined the method 'create_payment_procesor.
    
    Methods:

        create_payment_processor(type_payment_method: PaymentMethods) -> IPaymentPocessor:
            Create a payment processor based on the payment method.
    """
    @abstractmethod
    def create_payment_processor(self, payment_method: PaymentMethods) -> IPaymentProcessor: ...
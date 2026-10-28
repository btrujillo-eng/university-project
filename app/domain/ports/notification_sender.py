from abc import ABC, abstractmethod

from app.api.schemas import PaymentDataRequest, PaymentResponse


class INotificationChannel(ABC):
    """
    Interface for notification channels.
    
    Any class that implement this interface must define the methods 'notify_successful_payment' and
    notify_failed_payment
    
    Methods:
        notify_successful_payment(payment_data: BasePaymentData, payment_response: PaymentResponse) -> bool:
            Sends a notifications to the user when the payment has been successfully
            completed.
              
        notify_failed_payment(payment_data: BasePaymentData, payment_response: PaymentResponse) -> bool:
            Sends a notifications to the user when the payment has been rejected.
    """
    @abstractmethod
    async def notify_successful_payment(self, payment_data: PaymentDataRequest, payment_response: PaymentResponse) -> bool: ...
    
    @abstractmethod
    async def notify_failed_payment(self, payment_data: PaymentDataRequest, payment_response: PaymentResponse)  -> bool:...

class INotificationChannelTemplate(ABC):
    """
    Interface for notification channel templates.
    
    Any class that implement this interface must define the methods 'successful_payment_template' and
    'failed_payment_template'.
    
    Methods:
        successful_payment_template(payment_data: BasePaymentData, payment_response: PaymentResponse) -> str:
            It's responsible for storing the template to send the payment confirmation message.
            
        failed_payment_template(payment_data: BasePaymentData, payment_response: PaymentResponse) -> str:
            It's responsible for storing the template to send the payment error message.
    """
    @abstractmethod
    def successful_payment_template(self, payment_data: PaymentDataRequest, payment_response: PaymentResponse) -> str: ...
    
    @abstractmethod
    def failed_payment_template(self, payment_data: PaymentDataRequest, payment_response: PaymentResponse) -> str: ...

class INotificationService(ABC):
    """
    Interface for notification service.
    
    Any class that implement this interface must define the 'notify_all' method.
    
    Methods:
        notify_all(payment_response: PaymentResponse, payment_data: BasePaymentData) -> None:
            Is responsible for notifying the user through all notification channels.
        
    """
    @abstractmethod
    def notify_all(self, payment_response: PaymentResponse, payment_data: PaymentDataRequest) -> None: ...
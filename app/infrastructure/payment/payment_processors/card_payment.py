from app.api.schemas import PaymentDataRequest, PaymentResponse
from app.domain.ports import IPaymentGateway, IPaymentProcessor


class CardPaymentProcessor(IPaymentProcessor):
    def __init__(self, stripe_gateway: IPaymentGateway) -> None:
        self.stripe_gateway = stripe_gateway
    
    async def process(self, payment_data: PaymentDataRequest) -> PaymentResponse:
        payment_response = await self.stripe_gateway.process_payment(payment_data)
        
        return payment_response
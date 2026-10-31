from app.api.schemas import PaymentDataRequest, PaymentResponse
from app.domain.ports import IPaymentGateway, IPaymentProcessor


class CashPaymentProcessor(IPaymentProcessor):
    
    def __init__(self, cash_gateway: IPaymentGateway) -> None:
        self.cash_gateway = cash_gateway
    
    async def process(self, payment_data: PaymentDataRequest) -> PaymentResponse:
        response = await self.cash_gateway.process_payment(payment_data)
        
        return response
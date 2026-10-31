from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies.payment import get_process_payment
from app.api.schemas import PaymentDataRequest, PaymentResponse
from app.application import ProcessPaymentUseCase
from app.exceptions.errors import StripePaymentMethodError

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/", response_model=PaymentResponse)
async def process_payment(
    payment_data: PaymentDataRequest,
    process_payment: ProcessPaymentUseCase = Depends(get_process_payment),
) -> PaymentResponse:
    try:
        return await process_payment.process(payment_data)
    except StripePaymentMethodError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

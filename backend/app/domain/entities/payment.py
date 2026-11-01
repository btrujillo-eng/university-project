from dataclasses import dataclass

from app.domain.enums import PaymentMethods, PaymentStatus


@dataclass(frozen=True, slots=True)
class Payment:
    method: PaymentMethods
    status: PaymentStatus

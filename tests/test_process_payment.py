import asyncio
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.application.use_cases.process_payment import ProcessPaymentUseCase
from app.domain.enums import PaymentMethods


class FakePaymentData:
    def __init__(self, method: PaymentMethods, amount: Decimal) -> None:
        self.payment_method = SimpleNamespace(method=method)
        self.transaction_amount = amount
        self.discount_type = "no aplica"

    def model_copy(self, *, update: dict[str, object]) -> "FakePaymentData":
        return FakePaymentData(
            self.payment_method.method,
            update.get("transaction_amount", self.transaction_amount),
        )


class FakeShoppingCart:
    def calculate_total(self, payment_amount: Decimal, discount_type: str) -> Decimal:
        return payment_amount


class FakeProcessor:
    def __init__(self, response: SimpleNamespace) -> None:
        self.response = response
        self.received_data = None

    async def process(self, payment_data: FakePaymentData) -> SimpleNamespace:
        self.received_data = payment_data
        return self.response


class FakeFactory:
    def __init__(self, processor: FakeProcessor) -> None:
        self.processor = processor
        self.requested_method = None

    def create_payment_processor(self, payment_method: PaymentMethods) -> FakeProcessor:
        self.requested_method = payment_method
        return self.processor


class FakeNotificationService:
    def __init__(self) -> None:
        self.notifications = []

    def notify_all(
        self,
        payment_response: SimpleNamespace,
        payment_data: FakePaymentData,
    ) -> None:
        self.notifications.append((payment_response, payment_data))


@pytest.mark.parametrize(
    ("method", "status", "expected_notifications"),
    [
        (PaymentMethods.CARD, "succeeded", 1),
        (PaymentMethods.CARD, "failed", 0),
        (PaymentMethods.CASH, "succeeded", 0),
    ],
)
def test_payment_notifies_only_after_successful_card_payment(
    method: PaymentMethods,
    status: str,
    expected_notifications: int,
) -> None:
    response = SimpleNamespace(
        payment_status=status,
        payment_method=SimpleNamespace(method=method),
        transaction_amount=Decimal("25000.00"),
    )
    processor = FakeProcessor(response)
    factory = FakeFactory(processor)
    notifications = FakeNotificationService()
    use_case = ProcessPaymentUseCase(FakeShoppingCart(), factory, notifications)
    data = FakePaymentData(method, Decimal("25000.00"))

    result = asyncio.run(use_case.process(data))

    assert result is response
    assert factory.requested_method is method
    assert processor.received_data.transaction_amount == Decimal("25000.00")
    assert len(notifications.notifications) == expected_notifications


def test_notification_failure_does_not_fail_a_successful_charge() -> None:
    class FailingNotificationService:
        def notify_all(self, payment_response: SimpleNamespace, payment_data: FakePaymentData) -> None:
            raise RuntimeError("mail provider unavailable")

    response = SimpleNamespace(
        payment_status="succeeded",
        payment_method=SimpleNamespace(method=PaymentMethods.CARD),
        transaction_amount=Decimal("25000.00"),
    )
    processor = FakeProcessor(response)
    use_case = ProcessPaymentUseCase(
        FakeShoppingCart(),
        FakeFactory(processor),
        FailingNotificationService(),
    )

    result = asyncio.run(use_case.process(FakePaymentData(PaymentMethods.CARD, Decimal("25000.00"))))

    assert result is response

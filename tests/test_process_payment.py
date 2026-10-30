import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.application.use_cases.process_payment import ProcessPaymentUseCase
from app.domain.enums import PaymentMethods


class FakePaymentData:
    def __init__(self, method: PaymentMethods, amount: Decimal) -> None:
        self.payment_method = SimpleNamespace(method=method)
        self.transaction_amount = amount
        self.discount_type = "no_aplica"
        self.user_data = SimpleNamespace(
            first_name="Brayan",
            contact_info=SimpleNamespace(email="customer@example.com"),
        )

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


class FakeOutboxRepository:
    def __init__(self, should_fail: bool = False) -> None:
        self.events: list[dict[str, object]] = []
        self.should_fail = should_fail

    async def enqueue(self, **event: object) -> bool:
        if self.should_fail:
            raise RuntimeError("database unavailable")
        self.events.append(event)
        return True


def make_response(method: PaymentMethods, status: str) -> SimpleNamespace:
    payment_method = SimpleNamespace(method=method)
    if method is PaymentMethods.CARD:
        payment_method.processing_network = "Visa"
        payment_method.last_digits = "4242"
    return SimpleNamespace(
        payment_status=status,
        payment_method=payment_method,
        transaction_id="txn_123",
        transaction_amount=Decimal("25000.00"),
        currency=SimpleNamespace(value="cop"),
        created_at=datetime(2026, 10, 30, tzinfo=UTC),
    )


@pytest.mark.parametrize(
    ("method", "status", "expected_events"),
    [
        (PaymentMethods.CARD, "succeeded", 1),
        (PaymentMethods.CARD, "failed", 0),
        (PaymentMethods.CASH, "succeeded", 0),
    ],
)
def test_payment_enqueues_only_successful_card_confirmations(
    method: PaymentMethods,
    status: str,
    expected_events: int,
) -> None:
    response = make_response(method, status)
    processor = FakeProcessor(response)
    factory = FakeFactory(processor)
    outbox = FakeOutboxRepository()
    use_case = ProcessPaymentUseCase(FakeShoppingCart(), factory, outbox)

    result = asyncio.run(
        use_case.process(FakePaymentData(method, Decimal("25000.00")))
    )

    assert result is response
    assert factory.requested_method is method
    assert processor.received_data.transaction_amount == Decimal("25000.00")
    assert len(outbox.events) == expected_events
    if expected_events:
        event = outbox.events[0]
        assert event["event_key"] == "payment-confirmation:txn_123"
        assert event["event_type"] == "payment.card.succeeded"
        assert event["payload"]["email"] == "customer@example.com"


def test_outbox_failure_does_not_turn_approved_payment_into_api_failure() -> None:
    response = make_response(PaymentMethods.CARD, "succeeded")
    use_case = ProcessPaymentUseCase(
        FakeShoppingCart(),
        FakeFactory(FakeProcessor(response)),
        FakeOutboxRepository(should_fail=True),
    )

    result = asyncio.run(
        use_case.process(FakePaymentData(PaymentMethods.CARD, Decimal("25000.00")))
    )

    assert result is response

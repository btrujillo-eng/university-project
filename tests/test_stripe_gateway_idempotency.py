import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.api.schemas.payment import PaymentDataRequest
from app.api.schemas.user import ContactInfoRequest, UserDataRequest
from app.domain.enums import PaymentMethods, TypeCurrency
from app.infrastructure.payment.payment_gateways.stripe_gateway import StripeGateway


def test_stripe_gateway_passes_stable_idempotency_key(monkeypatch):
    payment_method_calls = []
    intent_calls = []

    def retrieve(payment_method_id):
        payment_method_calls.append(payment_method_id)
        return {"card": {"brand": "visa", "last4": "4242"}}

    def create(**kwargs):
        intent_calls.append(kwargs)
        return {
            "id": "pi_test_123",
            "status": "succeeded",
            "amount": 2500000,
            "created": int(datetime.now(UTC).timestamp()),
        }

    monkeypatch.setattr("app.infrastructure.payment.payment_gateways.stripe_gateway.stripe.PaymentMethod.retrieve", retrieve)
    monkeypatch.setattr("app.infrastructure.payment.payment_gateways.stripe_gateway.stripe.PaymentIntent.create", create)

    data = PaymentDataRequest(
        user_data=UserDataRequest(
            first_name="Brayan",
            first_surname="Trujillo",
            contact_info=ContactInfoRequest(email="brayan@example.com"),
        ),
        currency=TypeCurrency.COP,
        transaction_amount=Decimal("25000.00"),
        payment_method={"method": PaymentMethods.CARD, "payment_method_id": "pm_card_visa"},
        idempotency_key="checkout-7-unique-client-key-123",
    )

    result = asyncio.run(StripeGateway("sk_test_example").process_payment(data))

    assert result.payment_status == "succeeded"
    assert result.transaction_id == "pi_test_123"
    assert payment_method_calls == ["pm_card_visa"]
    assert intent_calls[0]["idempotency_key"] == "checkout-7-unique-client-key-123"
    assert intent_calls[0]["amount"] == 2500000


def test_payment_data_accepts_optional_internal_idempotency_key():
    data = PaymentDataRequest(
        user_data=UserDataRequest(
            first_name="Brayan",
            first_surname="Trujillo",
            contact_info=ContactInfoRequest(email="brayan@example.com"),
        ),
        transaction_amount=Decimal("25000.00"),
        payment_method={"method": "cash"},
    )

    assert data.idempotency_key is None

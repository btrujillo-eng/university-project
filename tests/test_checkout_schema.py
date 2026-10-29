import pytest
from pydantic import ValidationError

from app.api.schemas.order import CheckoutRequest


def _valid_checkout_payload() -> dict[str, object]:
    return {
        "shipping": {
            "street": "Calle 10 # 20-30",
            "neighborhood": "Laureles",
            "department": "Antioquia",
            "details": "Apto 301",
            "delivery_instructions": "Llamar al llegar",
            "city": "Medellin",
            "phone_number": "3001234567",
        },
        "payment_method": {"method": "cash"},
    }


def test_checkout_accepts_cash_payment_and_valid_shipping_data() -> None:
    checkout = CheckoutRequest.model_validate(_valid_checkout_payload())
    assert checkout.payment_method.method == "cash"
    assert checkout.shipping.phone_number == "3001234567"
    assert checkout.shipping.neighborhood == "Laureles"


def test_checkout_rejects_invalid_phone_number() -> None:
    payload = _valid_checkout_payload()
    payload["shipping"]["phone_number"] = "123"
    with pytest.raises(ValidationError):
        CheckoutRequest.model_validate(payload)


def test_checkout_rejects_card_data_without_stripe_payment_method_id() -> None:
    payload = _valid_checkout_payload()
    payload["payment_method"] = {
        "method": "card",
        "card_number": "4242424242424242",
        "cvv": "123",
    }
    with pytest.raises(ValidationError):
        CheckoutRequest.model_validate(payload)


def test_checkout_accepts_stripe_payment_method_id() -> None:
    payload = _valid_checkout_payload()
    payload["payment_method"] = {"method": "card", "payment_method_id": "pm_card_visa"}
    checkout = CheckoutRequest.model_validate(payload)
    assert checkout.payment_method.payment_method_id == "pm_card_visa"


def test_checkout_rejects_client_selected_discount() -> None:
    payload = _valid_checkout_payload()
    payload["discount_type"] = "black_friday"
    with pytest.raises(ValidationError):
        CheckoutRequest.model_validate(payload)

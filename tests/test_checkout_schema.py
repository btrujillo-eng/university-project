import pytest
from pydantic import ValidationError

from app.api.schemas.order import CheckoutRequest


def _valid_checkout_payload() -> dict[str, object]:
    return {
        "shipping": {
            "street": "Calle 10 # 20-30",
            "details": "Apto 301",
            "city": "Medellin",
            "phone_number": "3001234567",
        },
        "payment_method": {"method": "cash"},
    }


def test_checkout_accepts_cash_payment_and_valid_shipping_data() -> None:
    checkout = CheckoutRequest.model_validate(_valid_checkout_payload())
    assert checkout.payment_method.method == "cash"
    assert checkout.shipping.phone_number == "3001234567"


def test_checkout_rejects_invalid_phone_number() -> None:
    payload = _valid_checkout_payload()
    payload["shipping"] = {
        "street": "Calle 10 # 20-30",
        "details": "Apto 301",
        "city": "Medellin",
        "phone_number": "123",
    }
    with pytest.raises(ValidationError):
        CheckoutRequest.model_validate(payload)

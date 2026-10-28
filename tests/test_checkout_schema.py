import pytest
from pydantic import ValidationError

from app.api.schemas.order import CheckoutRequest


def _valid_checkout_payload() -> dict[str, object]:
    return {
        "items": [{"product_id": 1, "quantity": 2}],
        "shipping": {
            "street": "Calle 10 # 20-30",
            "details": "Apto 301",
            "city": "Medellin",
            "phone_number": "3001234567",
        },
        "payment_method": {"method": "cash"},
    }


def test_checkout_rejects_duplicate_product_lines() -> None:
    payload = _valid_checkout_payload()
    payload["items"] = [
        {"product_id": 1, "quantity": 1},
        {"product_id": 1, "quantity": 2},
    ]
    with pytest.raises(ValidationError):
        CheckoutRequest.model_validate(payload)


def test_checkout_rejects_non_positive_quantity() -> None:
    payload = _valid_checkout_payload()
    payload["items"] = [{"product_id": 1, "quantity": 0}]
    with pytest.raises(ValidationError):
        CheckoutRequest.model_validate(payload)


def test_checkout_accepts_cash_payment_and_valid_shipping_data() -> None:
    checkout = CheckoutRequest.model_validate(_valid_checkout_payload())
    assert checkout.items[0].quantity == 2
    assert checkout.shipping.phone_number == "3001234567"

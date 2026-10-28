import pytest
from pydantic import ValidationError

from app.api.schemas.cart import AddCartItemRequest


def test_add_cart_item_requires_positive_quantity() -> None:
    with pytest.raises(ValidationError):
        AddCartItemRequest(product_id=1, quantity=0)


def test_add_cart_item_accepts_valid_quantity() -> None:
    item = AddCartItemRequest(product_id=12, quantity=3)
    assert item.product_id == 12
    assert item.quantity == 3

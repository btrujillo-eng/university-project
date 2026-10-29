from decimal import Decimal
import pytest
from pydantic import ValidationError

from app.api.schemas.product import (
    ProductCreateRequest,
    ProductPriceUpdateRequest,
    ProductStockUpdateRequest,
)


def test_product_create_rejects_non_positive_price() -> None:
    with pytest.raises(ValidationError):
        ProductCreateRequest(
            name="Lentejas",
            section_id=1,
            price="0.00",
            stock=5,
            unit_of_measure="kilogram",
        )


def test_product_create_rejects_negative_stock() -> None:
    with pytest.raises(ValidationError):
        ProductCreateRequest(
            name="Lentejas",
            section_id=1,
            price="4500.00",
            stock=-1,
            unit_of_measure="kilogram",
        )


def test_product_price_update_rejects_zero() -> None:
    with pytest.raises(ValidationError):
        ProductPriceUpdateRequest(price="0.00")


def test_product_stock_update_accepts_zero() -> None:
    assert ProductStockUpdateRequest(stock=0).stock == 0



def test_product_create_accepts_fractional_weight_stock() -> None:
    product = ProductCreateRequest(
        name="Papa",
        section_id=1,
        price="4500.00",
        stock="12.500",
        unit_of_measure="kilogram",
    )
    assert product.stock == Decimal("12.500")


def test_product_create_rejects_fractional_stock_for_unit_products() -> None:
    with pytest.raises(ValidationError):
        ProductCreateRequest(
            name="Manzana",
            section_id=1,
            price="1200.00",
            stock="2.500",
            unit_of_measure="unit",
        )

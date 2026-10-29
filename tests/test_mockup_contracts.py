from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.api.schemas.order import CheckoutRequest, ShippingAddressRequest
from app.api.schemas.product import ProductResponse, ProductSectionResponse
from app.domain.enums import UnitOfMeasure


def test_shipping_request_accepts_mockup_delivery_fields() -> None:
    shipping = ShippingAddressRequest(
        street="Calle 10 # 20-30",
        neighborhood="Laureles",
        department="Antioquia",
        details="Casa blanca, portón negro",
        delivery_instructions="Llamar al llegar",
        city="Medellín",
        phone_number="3001234567",
    )
    assert shipping.neighborhood == "Laureles"
    assert shipping.delivery_instructions == "Llamar al llegar"


def test_shipping_request_requires_neighborhood_and_department() -> None:
    with pytest.raises(ValidationError):
        ShippingAddressRequest(
            street="Calle 10 # 20-30",
            details="Casa blanca",
            city="Medellín",
            phone_number="3001234567",
        )


def test_product_response_exposes_section_and_image() -> None:
    product = ProductResponse(
        id=1,
        name="Papa",
        section_id=2,
        section_name="Tubérculos",
        price=Decimal("4500.00"),
        stock=20,
        unit_of_measure=UnitOfMeasure.KILOGRAM,
        image_path="/media/products/example.webp",
    )
    assert product.section_name == "Tubérculos"
    assert product.image_path == "/media/products/example.webp"


def test_section_response_contract() -> None:
    assert ProductSectionResponse(id=2, name="Tubérculos").model_dump() == {
        "id": 2,
        "name": "Tubérculos",
    }

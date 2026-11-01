from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy.orm import configure_mappers

from app.api.v1.routers.order import _to_response
from app.domain.enums import DeliveryStatus, PaymentMethods, PaymentStatus
from app.infrastructure.persistence.models import Order, Payment


def test_order_and_payment_models_have_one_to_one_relationship() -> None:
    configure_mappers()

    assert Order.__table__.c.payment_id.unique is True
    assert Order.__table__.c.payment_id.foreign_keys
    assert "payment" in Order.__mapper__.relationships
    assert "order" in Payment.__mapper__.relationships


def test_order_response_reads_payment_fields_from_payment_relationship() -> None:
    order = SimpleNamespace(
        id=17,
        user_id=9,
        customer_name="Cliente",
        courier_id=None,
        total_price=Decimal("25000.00"),
        delivery_status=DeliveryStatus.PENDING,
        created_at=datetime(2026, 11, 1, tzinfo=UTC),
        shipping_street="Calle 10",
        shipping_neighborhood="Laureles",
        shipping_department="Antioquia",
        shipping_details="Apto 301",
        shipping_instructions=None,
        shipping_city="Medellín",
        phone_number="3001234567",
        order_items=[],
        payment=SimpleNamespace(
            method=PaymentMethods.CASH,
            status=PaymentStatus.PENDING,
        ),
    )

    response = _to_response(order)

    assert response.payment_method == PaymentMethods.CASH
    assert response.payment_status == PaymentStatus.PENDING

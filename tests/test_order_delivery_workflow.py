import pytest
from pydantic import ValidationError

from app.api.schemas.order import DeliveryStatusUpdateRequest
from app.domain.enums import DeliveryStatus
from app.domain.order_workflow import allowed_delivery_transitions
from app.api.v1.routers.order import _require_role
from app.domain.enums import UserRole, PaymentMethods, PaymentStatus
from app.domain.order_workflow import can_mark_order_delivered
from fastapi import HTTPException
from types import SimpleNamespace


@pytest.mark.parametrize(
    ("current", "expected"),
    [
        (DeliveryStatus.PACKAGED, {DeliveryStatus.IN_TRANSIT}),
        (
            DeliveryStatus.IN_TRANSIT,
            {DeliveryStatus.DELIVERED, DeliveryStatus.RETURNED_TO_WAREHOUSE},
        ),
        (DeliveryStatus.PENDING, set()),
        (DeliveryStatus.DELIVERED, set()),
        (DeliveryStatus.RETURNED_TO_WAREHOUSE, set()),
        (DeliveryStatus.CANCELED, set()),
    ],
)
def test_allowed_delivery_transitions_are_explicit(current, expected) -> None:
    assert allowed_delivery_transitions(current) == frozenset(expected)


def test_delivery_status_request_uses_json_field_and_rejects_extra_fields() -> None:
    request = DeliveryStatusUpdateRequest.model_validate(
        {"delivery_status": "returned_to_warehouse"}
    )
    assert request.delivery_status == DeliveryStatus.RETURNED_TO_WAREHOUSE

    with pytest.raises(ValidationError):
        DeliveryStatusUpdateRequest.model_validate(
            {"delivery_status": "delivered", "courier_id": 999}
        )


@pytest.mark.parametrize("invalid_status", ["canceled", "pending", "packaged", "unknown"])
def test_courier_request_schema_accepts_enum_values_only(invalid_status) -> None:
    if invalid_status == "canceled":
        # Canceled exists in the persistence enum but is not a courier transition.
        request = DeliveryStatusUpdateRequest(delivery_status=invalid_status)
        assert request.delivery_status == DeliveryStatus.CANCELED
        assert request.delivery_status not in allowed_delivery_transitions(DeliveryStatus.IN_TRANSIT)
    elif invalid_status == "pending":
        request = DeliveryStatusUpdateRequest(delivery_status=invalid_status)
        assert request.delivery_status not in allowed_delivery_transitions(DeliveryStatus.IN_TRANSIT)
    elif invalid_status == "packaged":
        request = DeliveryStatusUpdateRequest(delivery_status=invalid_status)
        assert request.delivery_status not in allowed_delivery_transitions(DeliveryStatus.IN_TRANSIT)
    else:
        with pytest.raises(ValidationError):
            DeliveryStatusUpdateRequest(delivery_status=invalid_status)


@pytest.mark.parametrize(
    ("role", "expected_allowed"),
    [
        (UserRole.STORE_MANAGER, True),
        (UserRole.WAREHOUSE_MANAGER, False),
        (UserRole.PACKAGING_MANAGER, False),
        (UserRole.COURIER, False),
        (UserRole.CUSTOMER, False),
    ],
)
def test_store_manager_role_is_required_for_store_manager_actions(role, expected_allowed) -> None:
    user = SimpleNamespace(user_role=role.value)
    if expected_allowed:
        _require_role(user, UserRole.STORE_MANAGER)
    else:
        with pytest.raises(HTTPException) as error:
            _require_role(user, UserRole.STORE_MANAGER)
        assert error.value.status_code == 403


@pytest.mark.parametrize(
    ("method", "payment_status", "expected"),
    [
        (PaymentMethods.CARD, PaymentStatus.SUCCEDED, True),
        (PaymentMethods.CARD, PaymentStatus.PENDING, True),
        (PaymentMethods.CASH, PaymentStatus.SUCCEDED, True),
        (PaymentMethods.CASH, PaymentStatus.PENDING, False),
        (PaymentMethods.CASH, PaymentStatus.FAILED, False),
    ],
)
def test_cash_order_must_be_paid_before_delivery(method, payment_status, expected) -> None:
    assert can_mark_order_delivered(method, payment_status) is expected

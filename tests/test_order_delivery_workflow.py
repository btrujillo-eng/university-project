import pytest
from pydantic import ValidationError

from app.api.schemas.order import DeliveryStatusUpdateRequest
from app.domain.enums import DeliveryStatus
from app.domain.order_workflow import allowed_delivery_transitions


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

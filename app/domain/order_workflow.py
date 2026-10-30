from app.domain.enums import DeliveryStatus


def allowed_delivery_transitions(current: DeliveryStatus) -> frozenset[DeliveryStatus]:
    """Return the only delivery states reachable from the current state."""
    transitions = {
        DeliveryStatus.PACKAGED: frozenset({DeliveryStatus.IN_TRANSIT}),
        DeliveryStatus.IN_TRANSIT: frozenset(
            {
                DeliveryStatus.DELIVERED,
                DeliveryStatus.RETURNED_TO_WAREHOUSE,
            }
        ),
    }
    return transitions.get(current, frozenset())

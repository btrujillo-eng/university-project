from app.domain.enums import DeliveryStatus, PaymentMethods, PaymentStatus


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


def can_mark_order_delivered(
    payment_method: PaymentMethods,
    payment_status: PaymentStatus,
) -> bool:
    """Cash orders must be confirmed as paid before delivery is completed."""
    return (
        payment_method != PaymentMethods.CASH
        or payment_status == PaymentStatus.SUCCEDED
    )

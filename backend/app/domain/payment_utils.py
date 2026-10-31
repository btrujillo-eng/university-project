from decimal import Decimal


def to_stripe_amount(payment_amount: Decimal) -> int:
    """
    It's responsible for transferring the payment amount to Stripe in the requested format.
    """
    return int(payment_amount * 100)
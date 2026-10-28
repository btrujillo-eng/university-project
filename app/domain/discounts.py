from decimal import Decimal

from app.domain.ports import IDiscountStrategy


class NoDiscount(IDiscountStrategy):
    def apply_discount(self, payment_amount: Decimal) -> Decimal:
        """
        Doesn't returns a discount value.
        """
        return Decimal(0)
    
class ChristmasDiscount(IDiscountStrategy):
    def apply_discount(self, payment_amount: Decimal) -> Decimal:
        """
        Returns a discount value of 30%.
        """
        discount_value = payment_amount * Decimal("0.30")
        return discount_value
    
class FixedDiscount(IDiscountStrategy):
    def apply_discount(self, payment_amount: Decimal) -> Decimal:
        """
        Returns a fixed discount value of 5000 if the purchase amount
        is greater than 15000. If purchase amount is less than 15000,
        doesn't return a discount value.
        """
        if payment_amount >= Decimal(15000):
            return Decimal(5000)
        return Decimal(0)
    
class BlackFridayDiscount(IDiscountStrategy):
    def apply_discount(self, payment_amount: Decimal) -> Decimal:
        """
        Returns a discount value of 20%.
        """
        discount_value = payment_amount * Decimal("0.20")
        return discount_value
    
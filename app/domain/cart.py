from decimal import ROUND_HALF_UP, Decimal

from app.domain.enums import DiscountStrategy
from app.domain.ports import IDiscountStrategy, IShoppingCart
from app.domain.strategies import get_discount_strategy


class ShoppingCart(IShoppingCart):
    def __init__(self, strategy_map: dict[DiscountStrategy, IDiscountStrategy], default_discount: IDiscountStrategy) -> None:
        self.strategy_map = strategy_map
        self.default_discount = default_discount
    
    def calculate_total(self, payment_amount: Decimal, discount_type: DiscountStrategy | str) -> Decimal:
        """
        Apply a discount type to the purchase and calculate
        the total price.
        """
        discount_strategy = get_discount_strategy(discount_type, self.strategy_map, self.default_discount)
        discount_value =  discount_strategy.apply_discount(payment_amount)
        discount_amount = discount_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_price = payment_amount - discount_amount
        
        return total_price
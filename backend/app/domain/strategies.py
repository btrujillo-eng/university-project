import logging

from app.domain.constants import NOTIFICATION_METHOD
from app.domain.enums import DiscountStrategy, PaymentStatus
from app.domain.ports import IDiscountStrategy, INotificationChannel
from app.exceptions import StrategyValueNotFoundError

logger = logging.getLogger(__name__)
   
def get_discount_strategy(
        discount_type: DiscountStrategy | str,
        strategy_map: dict[DiscountStrategy, IDiscountStrategy],
        default: IDiscountStrategy | None = None
    ) -> IDiscountStrategy:
    """
    It searches a strategic discount and returns it dependig on the discount type.
    
    The discount type could be 'no aplica', 'navidad', 'fijo' or 'black friday'.
    """
    try:
        discount_type = DiscountStrategy(discount_type.strip().lower())
    except ValueError:
        discount_type = DiscountStrategy.NODISCOUNT
            
    default_class = default
    strategy_class = strategy_map.get(discount_type, default_class)
    
    if not strategy_class:
        logger.critical("No default strategy was found on the map")
        raise StrategyValueNotFoundError("Critical error: No default strategy was found on the map")
    
    return strategy_class

def get_payment_status(payment_status: PaymentStatus | str, default: PaymentStatus) -> PaymentStatus:
    """
    It is responsible for finding the payment status.
    """
    try:
        payment_status = PaymentStatus(payment_status.strip().lower())
    except ValueError:
        return default
            
    return payment_status
    
def get_notification_method(payment_status: str, channel_instance: INotificationChannel):
    """
    It is responsible for finding the notification method.
    """
    status = get_payment_status(payment_status, PaymentStatus.FAILED)
    method_name = NOTIFICATION_METHOD.get(status)
    if not method_name:
        method_name = 'notify_failed_payment'
    
    # getattr is used to dynamically search for a method in its object or instance using its name in str.
    method = getattr(channel_instance, method_name)
    return method
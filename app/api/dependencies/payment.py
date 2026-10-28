from fastapi import Depends

from app.application import ProcessPaymentUseCase
from app.domain.cart import ShoppingCart
from app.domain.discounts import (
    BlackFridayDiscount,
    ChristmasDiscount,
    FixedDiscount,
    NoDiscount,
)
from app.domain.enums import DiscountStrategy
from app.domain.factory import PaymentMethodFactory
from app.domain.ports import IDiscountStrategy, INotificationChannel
from app.infrastructure.config import Settings, get_settings
from app.infrastructure.notifications import (
    EmailChannel,
    EmailChannelTemplate,
    NotificationService,
)
from app.infrastructure.payment import (
    CardPaymentProcessor,
    CashGateway,
    CashPaymentProcessor,
    StripeGateway,
)


def get_cash_gateway() -> CashGateway:
    return CashGateway()

def get_stripe_gateway(settings:  Settings = Depends(get_settings)) -> StripeGateway:
    return StripeGateway(settings.stripe_api_key.get_secret_value())

def get_cash_payment_processor(cash_gateway: CashGateway = Depends(get_cash_gateway)) -> CashPaymentProcessor:
    return CashPaymentProcessor(cash_gateway)

def get_card_processor(stripe: StripeGateway = Depends(get_stripe_gateway)) -> CardPaymentProcessor:
    return CardPaymentProcessor(stripe)

def get_payment_method_factory(
        card_processor: CardPaymentProcessor = Depends(get_card_processor),
        cash_processor: CashPaymentProcessor = Depends(get_cash_payment_processor)
    ) -> PaymentMethodFactory:
    return PaymentMethodFactory(card_processor, cash_processor)

def get_strategy_map() -> dict[DiscountStrategy, IDiscountStrategy]:
    return {
        DiscountStrategy.NODISCOUNT: NoDiscount(),
        DiscountStrategy.CHRISTMAS: ChristmasDiscount(),
        DiscountStrategy.FIXED: FixedDiscount(),
        DiscountStrategy.BLACKFRIDAY: BlackFridayDiscount()
    }

def get_default_discount() -> IDiscountStrategy:
    return NoDiscount()

def get_shopping_cart(
        strategy_map: dict[DiscountStrategy, IDiscountStrategy] = Depends(get_strategy_map),
        default_discount: IDiscountStrategy = Depends(get_default_discount)
    ) -> ShoppingCart:
    return ShoppingCart(strategy_map, default_discount)

def get_notification_channels() -> list[INotificationChannel]:
    email_template = EmailChannelTemplate()
    return [
        EmailChannel(email_template),
    ]

def get_notification_service(
        notification_channels: list[INotificationChannel] = Depends(get_notification_channels)
    ) -> NotificationService:
    return NotificationService(notification_channels)

def get_process_payment(
        shopping_cart: ShoppingCart = Depends(get_shopping_cart),
        payment_method_factory: PaymentMethodFactory = Depends(get_payment_method_factory),
        notification_service: NotificationService = Depends(get_notification_service)
    ) -> ProcessPaymentUseCase:
    return ProcessPaymentUseCase(shopping_cart, payment_method_factory, notification_service)
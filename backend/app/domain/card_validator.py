import logging

from app.domain.card_utils import (
    get_processing_network,
    luhn_algorithm,
    validate_card_length,
)
from app.exceptions import CardPaymentMethodError

logger = logging.getLogger(__name__)

class CardValidator:
    def __call__(self, card_number: str) -> str:
        """
        Valid if a card is valid based on his number.
        
        For the validation of the card this method is based
        on three steps.
        
        1. Search for a processing network based on his IIN Prefixe.
        
        2. Valid if the card number length is valid, depending on his processing network.
        
        3. Used the luhn algorit for calculate if the card number is mathematically correct.
        
        if the card is valid returns the card number, otherwise returns raise CardPaymentMethodError.
        """
        processing_network = get_processing_network(card_number)
        if not processing_network:
            logger.warning("Unrecognized processing network for card number: %s", card_number)
            raise CardPaymentMethodError("The card processing network is not supported")
        
        if not validate_card_length(processing_network, card_number):
            logger.info("The entered card number is not valid for: %s", processing_network)
            raise CardPaymentMethodError(f"The card number legth is not valid for {processing_network}")
        
        if not luhn_algorithm(card_number):
            logger.info("Luhn error")
            raise CardPaymentMethodError("The card number is invalid")
        
        return card_number
from app.domain.constants import PROCESSING_NETWORK_RULES
from app.exceptions import CardPaymentMethodError


def get_processing_network(card_number: str) -> str | None:
    """
    Search for a processing network based on the card number.
    """
    iin_code = int(card_number[:4])
    for network in PROCESSING_NETWORK_RULES:
        if card_number.startswith(network['prefixes']):
            return network['name']

        for start, end in network['ranges']:
            if start <= iin_code <= end:
                return network['name']
            
    return None

def luhn_algorithm(card_number: str) -> bool:
    """
    Valid if the card number is mathematically correct.
    """
    position = 1
    total_sum = 0
    
    number = int(card_number)
    while number > 0:
        last_digit = number % 10
        
        if position % 2 == 0:
            new_value = last_digit * 2
        
            if new_value > 9:
                new_value -= 9
            total_sum += new_value
        else:
            total_sum += last_digit
            
        number = number // 10
        position += 1
        
    return total_sum % 10 == 0     

def validate_card_length(processing_network: str, card_number: str) -> bool:
    """
    Valid if the card number length is valid, depending
    on your processing network.
    """
    for rule in PROCESSING_NETWORK_RULES:
        if rule['name'] == processing_network:
            return len(card_number) in rule['lengths']
    
    return False
 
def validate_cvv_card(cvv: str, card_number: str) -> bool:
    processing_network = get_processing_network(card_number)
    if not processing_network:
        raise CardPaymentMethodError("The card number is invalid")
    
    for rule in PROCESSING_NETWORK_RULES:
        if rule['name'] == processing_network and rule['cvv_length'] == len(cvv):
            return True
        
    return False
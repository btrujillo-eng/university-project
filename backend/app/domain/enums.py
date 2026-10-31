from enum import Enum


class DiscountStrategy(str, Enum):
    NODISCOUNT = "no_aplica"
    CHRISTMAS = "navidad"
    FIXED = "fijo"
    BLACKFRIDAY = "black_friday"

class PaymentMethods(str, Enum):
    CARD = "card"
    CASH = "cash"

class PaymentStatus(str, Enum):
    SUCCEDED = "succeeded"
    FAILED = "failed"
    PENDING = "pending"
    
class TypeCurrency(str, Enum):
    USD = "usd"
    COP = "cop"
    
class UserRole(str, Enum):
    STORE_MANAGER = "store_manager"
    CUSTOMER = "customer"
    PACKAGING_MANAGER = "packaging_manager"
    WAREHOUSE_MANAGER = "warehouse_manager"
    COURIER = "courier"
    
class UnitOfMeasure(str, Enum):
    KILOGRAM = "kilogram"
    GRAM = "gram"
    POUND = "pound"
    UNIT = "unit"
    
class DeliveryStatus(str, Enum):
    PENDING = "pending"
    PACKAGED = "packaged"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELED = "canceled"
    RETURNED_TO_WAREHOUSE = "returned_to_warehouse"
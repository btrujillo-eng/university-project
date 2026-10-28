from abc import ABC, abstractmethod

from app.domain.enums import DeliveryStatus
from app.infrastructure.persistence.models.orders import Order


class IOrderRepository(ABC):
    @abstractmethod
    async def get_by_id_for_update(self, order_id: int) -> Order | None: ...

    @abstractmethod
    async def get_customer_orders(self, user_id: int) -> list[Order]: ...

    @abstractmethod
    async def list_by_delivery_status(self, status: DeliveryStatus) -> list[Order]: ...

    @abstractmethod
    async def list_for_courier(self, courier_id: int) -> list[Order]: ...

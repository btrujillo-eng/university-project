from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.enums import DeliveryStatus
from app.domain.ports.order_repository import IOrderRepository
from app.infrastructure.persistence.models.order_items import OrderItem
from app.infrastructure.persistence.models.orders import Order


class OrderRepository(IOrderRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _base_statement(self):
        return select(Order).options(
            selectinload(Order.order_items).selectinload(OrderItem.product)
        )

    async def get_by_id_for_update(self, order_id: int) -> Order | None:
        statement = self._base_statement().where(Order.id == order_id).with_for_update()
        return await self.session.scalar(statement)

    async def get_customer_orders(self, user_id: int, limit: int = 50, offset: int = 0) -> list[Order]:
        statement = self._base_statement().where(Order.user_id == user_id).order_by(Order.created_at.desc(), Order.id.desc()).limit(limit).offset(offset)
        return list((await self.session.scalars(statement)).all())

    async def list_all(self, limit: int = 50, offset: int = 0) -> list[Order]:
        statement = self._base_statement().order_by(Order.created_at.desc(), Order.id.desc()).limit(limit).offset(offset)
        return list((await self.session.scalars(statement)).all())

    async def list_by_delivery_status(self, status: DeliveryStatus, limit: int = 50, offset: int = 0) -> list[Order]:
        statement = self._base_statement().where(Order.delivery_status == status).order_by(Order.created_at.asc(), Order.id.asc()).limit(limit).offset(offset)
        return list((await self.session.scalars(statement)).all())

    async def list_for_courier(self, courier_id: int, limit: int = 50, offset: int = 0) -> list[Order]:
        statement = self._base_statement().where(Order.courier_id == courier_id).order_by(Order.created_at.asc(), Order.id.asc()).limit(limit).offset(offset)
        return list((await self.session.scalars(statement)).all())

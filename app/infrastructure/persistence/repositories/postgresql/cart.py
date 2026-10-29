from decimal import Decimal

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import ProductDoesNotExistError, ProductQuantityInvalidError, ProductStockInsufficientError
from app.domain.enums import UnitOfMeasure
from app.infrastructure.persistence.models.cart_items import CartItem
from app.infrastructure.persistence.models.carts import Cart
from app.infrastructure.persistence.models.products import Product


class CartRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _cart_statement(self):
        return select(Cart).options(selectinload(Cart.items).selectinload(CartItem.product))

    async def get_cart(self, user_id: int) -> Cart | None:
        statement = self._cart_statement().where(Cart.user_id == user_id)
        return await self.session.scalar(statement)

    async def get_cart_for_update(self, user_id: int) -> Cart | None:
        statement = self._cart_statement().where(Cart.user_id == user_id).with_for_update()
        return await self.session.scalar(statement)

    async def add_item(self, user_id: int, product_id: int, quantity: Decimal) -> None:
        # Lock order is always cart first, then product, matching checkout and avoiding deadlocks.
        cart = await self.get_cart_for_update(user_id)
        if cart is None:
            await self.session.execute(
                pg_insert(Cart).values(user_id=user_id).on_conflict_do_nothing(index_elements=[Cart.user_id])
            )
            cart = await self.get_cart_for_update(user_id)
        if cart is None:
            raise RuntimeError("No fue posible obtener el carrito del cliente")

        product_statement = select(Product).where(Product.id == product_id).with_for_update()
        product = await self.session.scalar(product_statement)
        if product is None:
            raise ProductDoesNotExistError("El producto no existe")

        if product.unit_of_measure == UnitOfMeasure.UNIT and quantity != quantity.to_integral_value():
            raise ProductQuantityInvalidError("Los productos vendidos por unidad requieren cantidades enteras")

        if product.unit_of_measure == UnitOfMeasure.UNIT and quantity != quantity.to_integral_value():
            raise ProductQuantityInvalidError("Los productos vendidos por unidad requieren cantidades enteras")

        existing_item = next((item for item in cart.items if item.product_id == product_id), None)
        new_quantity = quantity + (existing_item.quantity if existing_item is not None else 0)
        if product.stock < new_quantity:
            raise ProductStockInsufficientError(
                f"Stock insuficiente. Disponible: {product.stock}; solicitado: {new_quantity}"
            )
        if existing_item is None:
            cart.items.append(CartItem(product=product, product_id=product_id, quantity=quantity))
        else:
            existing_item.quantity = new_quantity
        await self.session.flush()

    async def remove_item(self, user_id: int, product_id: int) -> bool:
        cart = await self.get_cart_for_update(user_id)
        if cart is None:
            return False
        item = next((entry for entry in cart.items if entry.product_id == product_id), None)
        if item is None:
            return False
        cart.items.remove(item)
        await self.session.flush()
        return True
